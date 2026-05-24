"""Kiro CLI adapter.

Layout emitted under ``build/Kiro/``::

    steering/AGENTS.md              # always-on instructions (applyTo **), concatenated; NO frontmatter
    steering/<name>.md              # narrow-applyTo instructions with inclusion: fileMatch
    agents/<name>.json              # CLI custom agents (JSON format)
    prompts/<name>.md               # agent system prompts (body only) + source prompts
    skills/<native>/                # native skills from source/skills (passthrough)

Install targets:
* ``steering/``  -> ``%USERPROFILE%\\.kiro\\steering``
* ``agents/``    -> ``%USERPROFILE%\\.kiro\\agents``
* ``prompts/``   -> ``%USERPROFILE%\\.kiro\\prompts``
* ``skills/``    -> ``%USERPROFILE%\\.kiro\\skills``

Mapping rules (CLI only):

* ``applyTo: "**"`` instructions
    -> ``steering/AGENTS.md`` (pure Markdown, no frontmatter; always included by Kiro CLI)
* narrow ``applyTo`` instructions
    -> ``steering/<name>.md`` with ``inclusion: fileMatch`` + inline JSON ``fileMatchPattern``
* ``source/agents/``
    -> ``agents/<name>.json`` (CLI JSON format) + ``prompts/<name>.md`` (system prompt body)
       The JSON references the prompt via ``"prompt": "file://../prompts/<name>.md"``
       user-invocable: true  => primary agent tools (read/write/shell/code/@builtin)
       otherwise             => subagent tools (read/code)
* ``source/skills/``
    -> passthrough (SKILL.md frontmatter is identical)
* ``source/prompts/``
    -> ``prompts/<name>.md`` (strip Copilot frontmatter, keep body only)
       Referenced in chat via ``@<name>``
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from ..base import (
    AgentSource,
    BuildReport,
    InstallMapping,
    InstructionSource,
    PlatformAdapter,
    PromptSource,
    SourceBundle,
    clean_dir,
    copy_skill_tree,
    extract_scalar,
    register,
)


_AGENTS_MD_SEPARATOR = "\n\n---\n\n"

_TOOLS_PRIMARY = ["read", "write", "shell", "code", "@builtin"]
_TOOLS_SUBAGENT = ["read", "code"]
_ALLOWED_TOOLS_DEFAULT = ["read"]


def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _render_agent_json(agent: AgentSource) -> tuple[str, str]:
    """Return (agent_json_str, prompt_md_str).

    The agent JSON references its system prompt via file://../prompts/<name>.md
    so the prompt body is stored separately.
    """
    fm = agent.frontmatter_raw
    model = extract_scalar(fm, "model") or ""
    user_invocable = (extract_scalar(fm, "user-invocable") or "").strip().lower()
    is_primary = user_invocable == "true"

    obj: dict[str, Any] = {
        "name": agent.name,
        "description": agent.description or "",
        "prompt": f"file://../prompts/{agent.name}.md",
        "includeMcpJson": True,
        "tools": _TOOLS_PRIMARY if is_primary else _TOOLS_SUBAGENT,
        "allowedTools": _ALLOWED_TOOLS_DEFAULT,
    }
    if model:
        obj["model"] = model

    agent_json = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    prompt_md = agent.body.lstrip("\n")
    if not prompt_md.endswith("\n"):
        prompt_md += "\n"
    return agent_json, prompt_md


def _render_steering_agents_md(always_on: list[InstructionSource]) -> str:
    """Concatenate always-on instructions into steering/AGENTS.md.

    Kiro CLI AGENTS.md must have NO frontmatter.
    """
    parts = [ins.body.strip() for ins in always_on]
    return _AGENTS_MD_SEPARATOR.join(parts) + "\n"


def _render_steering_file(ins: InstructionSource) -> str:
    """Render a narrow-applyTo instruction as a Kiro steering file.

    Uses ``inclusion: fileMatch`` with inline JSON array for ``fileMatchPattern``
    as required by the Kiro frontmatter spec.
    """
    patterns = [p.strip() for p in ins.apply_to.split(",") if p.strip()]
    items = ", ".join(f'"{p}"' for p in patterns)
    pattern_value = f"[{items}]"

    lines = [
        "---",
        "inclusion: fileMatch",
        f"fileMatchPattern: {pattern_value}",
    ]
    if ins.description:
        lines.append(f'description: "{_yaml_escape(ins.description)}"')
    lines.append("---")
    lines.append("")
    lines.append(ins.body.lstrip("\n"))
    return "\n".join(lines)


def _strip_copilot_frontmatter(raw: str) -> str:
    """Return the body of a Copilot-style .prompt.md with frontmatter removed."""
    lines = raw.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), None)
        if end is not None:
            return "".join(lines[end + 1:]).lstrip("\n")
    return raw


class KiroAdapter(PlatformAdapter):
    name = "kiro"
    display_name = "Kiro"

    def build(self, source: SourceBundle, out_root: Path) -> BuildReport:
        report = BuildReport(platform=self.display_name, out_root=out_root)

        steering_out = out_root / "steering"
        agents_out = out_root / "agents"
        prompts_out = out_root / "prompts"
        skills_out = out_root / "skills"

        clean_dir(steering_out)
        clean_dir(agents_out)
        clean_dir(prompts_out)
        clean_dir(skills_out)

        # 1. agents -> <name>.json + prompts/<name>.md
        for agent in source.agents:
            agent_json, prompt_md = _render_agent_json(agent)
            (agents_out / f"{agent.name}.json").write_text(agent_json, encoding="utf-8")
            (prompts_out / f"{agent.name}.md").write_text(prompt_md, encoding="utf-8")
            report.agents_written += 1

        # 2. native skills: direct copy
        for skill in source.skills:
            copy_skill_tree(skill.path, skills_out / skill.name)
            report.skills_written += 1

        # 3. instructions
        always_on: list[InstructionSource] = []
        narrow: list[InstructionSource] = []
        for ins in source.instructions:
            (always_on if ins.always_on else narrow).append(ins)

        if always_on:
            (steering_out / "AGENTS.md").write_text(
                _render_steering_agents_md(always_on), encoding="utf-8"
            )
            report.instructions_written += len(always_on)

        for ins in narrow:
            (steering_out / f"{ins.name}.md").write_text(
                _render_steering_file(ins), encoding="utf-8"
            )
            report.instructions_written += 1

        # 4. source prompts -> prompts/<name>.md (strip Copilot frontmatter)
        for prompt in source.prompts:
            raw = prompt.path.read_text(encoding="utf-8")
            body = _strip_copilot_frontmatter(raw)
            if not body.endswith("\n"):
                body += "\n"
            (prompts_out / f"{prompt.name}.md").write_text(body, encoding="utf-8")
            report.prompts_written += 1

        return report

    def install_targets(self) -> Iterable[InstallMapping]:
        root = "${USERPROFILE}/.kiro"
        return (
            InstallMapping("steering", f"{root}/steering"),
            InstallMapping("agents", f"{root}/agents"),
            InstallMapping("prompts", f"{root}/prompts"),
            InstallMapping("skills", f"{root}/skills"),
        )


register(KiroAdapter())

