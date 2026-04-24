"""Codex adapter: frontmatter markdown -> TOML + AGENTS.md + skills.

Layout emitted under ``build/Codex/``::

    .codex/agents/<name>.toml            # custom SubAgent defs
    .codex/AGENTS.md                     # concatenated always-on instructions
    .agents/skills/<name>/...             # skills (from source/skills + derived
                                          # from narrow-applyTo instructions)

Install targets (see docs/codex-reference.md):
* ``.codex/agents/``    -> ``%USERPROFILE%\\.codex\\agents``
* ``.codex/AGENTS.md``  -> ``%USERPROFILE%\\.codex\\AGENTS.md``
* ``.agents/skills/``   -> ``%USERPROFILE%\\.agents\\skills``

Mapping rules for Copilot instructions:
* ``applyTo: "**"``        -> concatenated into ``AGENTS.md``
* narrower ``applyTo``     -> converted to a Codex skill whose ``description``
                               encodes the trigger condition so Codex picks it
                               up automatically.

Copilot prompts are dropped (Codex has no slash-command mechanism).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..base import (
    AgentSource,
    BuildReport,
    InstallMapping,
    InstructionSource,
    PlatformAdapter,
    SourceBundle,
    clean_dir,
    copy_skill_tree,
    register,
)


_AGENTS_MD_SEPARATOR = "\n\n---\n\n"


def _toml_basic_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _toml_multiline_literal(body: str) -> str:
    """Encode body as TOML multi-line string.

    Prefers literal (``'''``) to avoid escaping markdown. Falls back to basic
    multi-line with escaping when the body contains ``'''``.
    """
    if "'''" not in body:
        if not body.endswith("\n"):
            body = body + "\n"
        return "'''\n" + body + "'''"
    escaped = body.replace("\\", "\\\\").replace('"""', '\\"""')
    if not escaped.endswith("\n"):
        escaped += "\n"
    return '"""\n' + escaped + '"""'


def _render_agent_toml(agent: AgentSource) -> str:
    out: list[str] = []
    out.append(f"name = {_toml_basic_string(agent.name)}")
    out.append(f"description = {_toml_basic_string(agent.description)}")
    out.append("")
    body = agent.body.lstrip("\n")
    out.append("developer_instructions = " + _toml_multiline_literal(body))
    out.append("")
    return "\n".join(out)


def _render_agents_md(always_on: list[InstructionSource]) -> str:
    """Concatenate always-on instructions into a single AGENTS.md."""
    if not always_on:
        return ""
    parts = [ins.body.strip() for ins in always_on]
    return _AGENTS_MD_SEPARATOR.join(parts) + "\n"


def _render_instruction_skill(ins: InstructionSource) -> tuple[str, str]:
    """Render a narrow-applyTo instruction as a Codex SKILL.md.

    Returns ``(skill_name, skill_md_text)``. Codex Skill frontmatter only needs
    ``name`` and ``description``; the ``applyTo`` glob is inlined into the
    description so the Skill-selection model sees the trigger condition.
    """
    skill_name = ins.name
    trigger_hint = f"Use when editing files matching: {ins.apply_to}" if ins.apply_to else ""
    desc = ins.description.strip()
    if trigger_hint and trigger_hint not in desc:
        desc = f"{desc} {trigger_hint}".strip()

    # YAML-safe scalar: escape double quotes, collapse newlines
    desc_safe = desc.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()

    front = (
        "---\n"
        f"name: {skill_name}\n"
        f'description: "{desc_safe}"\n'
        "---\n\n"
    )
    body = ins.body.lstrip("\n")
    if not body.endswith("\n"):
        body += "\n"
    return skill_name, front + body


class CodexAdapter(PlatformAdapter):
    name = "codex"
    display_name = "Codex"

    def build(self, source: SourceBundle, out_root: Path) -> BuildReport:
        report = BuildReport(platform=self.display_name, out_root=out_root)

        agents_out = out_root / ".codex" / "agents"
        skills_out = out_root / ".codex" / "skills"
        agents_md_path = out_root / ".codex" / "AGENTS.md"
        clean_dir(agents_out)
        clean_dir(skills_out)
        agents_md_path.parent.mkdir(parents=True, exist_ok=True)
        if agents_md_path.exists():
            agents_md_path.unlink()

        # 1. agents
        for agent in source.agents:
            (agents_out / f"{agent.name}.toml").write_text(
                _render_agent_toml(agent), encoding="utf-8"
            )
            report.agents_written += 1

        # 2. native skills (copied as-is)
        for skill in source.skills:
            copy_skill_tree(skill.path, skills_out / skill.name)
            report.skills_written += 1

        # 3. instructions split: always-on -> AGENTS.md, narrow -> skill
        always_on: list[InstructionSource] = []
        narrow: list[InstructionSource] = []
        for ins in source.instructions:
            (always_on if ins.always_on else narrow).append(ins)

        if always_on:
            agents_md_path.write_text(_render_agents_md(always_on), encoding="utf-8")
            report.instructions_written += len(always_on)

        for ins in narrow:
            skill_name, text = _render_instruction_skill(ins)
            target_dir = skills_out / skill_name
            if target_dir.exists():
                report.warnings.append(
                    f"skill name collision: '{skill_name}' from instruction overlaps native skill — instruction skipped"
                )
                continue
            target_dir.mkdir(parents=True)
            (target_dir / "SKILL.md").write_text(text, encoding="utf-8")
            report.skills_written += 1
            report.instructions_written += 1

        # 4. prompts: intentionally dropped
        if source.prompts:
            report.warnings.append(
                f"{len(source.prompts)} prompt(s) dropped — Codex has no slash-prompt mechanism"
            )

        return report

    def install_targets(self) -> Iterable[InstallMapping]:
        # Precise subdirectories — never replace the entire ``.codex`` or
        # ``.agents`` roots (they contain Codex runtime state: logs,
        # config.toml, hooks.json, ...).
        return (
            InstallMapping(".codex/agents", "${USERPROFILE}/.codex/agents"),
            InstallMapping(".codex/AGENTS.md", "${USERPROFILE}/.codex/AGENTS.md"),
            InstallMapping(".codex/skills", "${USERPROFILE}/.codex/skills"),
        )


register(CodexAdapter())
