"""Windsurf adapter.

Layout emitted under ``build/Windsurf/``::

    memories/global_rules.md                # always-on core (AGENTS.md) + skill-load directive
    skills/agent-rules/SKILL.md             # merged: all other instructions
    skills/<native>/                         # native skills from source/skills (passthrough)
    global_workflows/<name>.md              # from source/prompts/<name>.prompt.md

Install targets (see docs/windsurf-reference.md):
* ``memories/``          -> ``%USERPROFILE%\\.codeium\\windsurf\\memories``
* ``skills/``            -> ``%USERPROFILE%\\.codeium\\windsurf\\skills``
* ``global_workflows/``  -> ``%USERPROFILE%\\.codeium\\windsurf\\global_workflows``

Mapping rules:

* ``source/agents/``           -> dropped. Windsurf has no custom-agent spec.
* ``source/skills/``           -> copied verbatim (format identical).
* ``source/instructions/AGENTS.md.instructions.md`` (core always-on)
    -> ``memories/global_rules.md`` with appended directive binding
       ``agent-rules`` skill.
* ``source/instructions/*`` (everything else)
    -> merged into one ``agent-rules`` skill whose description declares it
       must be loaded on every task (bi-directional binding with global_rules).
* ``source/prompts/*.prompt.md`` -> ``global_workflows/<name>.md`` (identical
    slash-command semantics).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from ..base import (
    BuildReport,
    InstallMapping,
    InstructionSource,
    PlatformAdapter,
    SourceBundle,
    clean_dir,
    copy_skill_tree,
    register,
)


_MERGED_SKILL_NAME = "agent-rules"

_MERGED_SKILL_DESCRIPTION = (
    "MUST load on every task. Core engineering rules bundle: "
    "context engineering, todo management, development environment, "
    "code quality (general + language-specific: python, typescript, java, "
    "sql), UI design. Referenced by global_rules.md as mandatory."
)

_GLOBAL_RULES_CONTENT = f"每次任务开始时必须加载 skill: `{_MERGED_SKILL_NAME}`。\n"

_SECTION_SEPARATOR = "\n\n---\n\n"


def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _render_merged_skill(always_on: list[InstructionSource]) -> str:
    """Concatenate all always-on (applyTo **) instructions into agent-rules/SKILL.md."""
    front = (
        "---\n"
        f"name: {_MERGED_SKILL_NAME}\n"
        f'description: "{_yaml_escape(_MERGED_SKILL_DESCRIPTION)}"\n'
        "---\n\n"
    )
    sections = [ins.body.strip() for ins in always_on]
    return front + _SECTION_SEPARATOR.join(sections) + "\n"


def _render_instruction_skill(ins: InstructionSource) -> tuple[str, str]:
    """Render a narrow-applyTo instruction as an individual Windsurf SKILL.md."""
    skill_name = ins.name
    trigger_hint = f"Use when editing files matching: {ins.apply_to}" if ins.apply_to else ""
    desc = ins.description.strip()
    if trigger_hint and trigger_hint not in desc:
        desc = f"{desc} {trigger_hint}".strip()
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


class WindsurfAdapter(PlatformAdapter):
    name = "windsurf"
    display_name = "Windsurf"

    def build(self, source: SourceBundle, out_root: Path) -> BuildReport:
        report = BuildReport(platform=self.display_name, out_root=out_root)

        memories_out = out_root / "memories"
        skills_out = out_root / "skills"
        workflows_out = out_root / "global_workflows"
        clean_dir(memories_out)
        clean_dir(skills_out)
        clean_dir(workflows_out)

        # 1. agents intentionally dropped
        if source.agents:
            report.warnings.append(
                f"{len(source.agents)} agent(s) dropped — Windsurf has no custom-agent spec"
            )

        # 2. native skills: direct copy
        for skill in source.skills:
            copy_skill_tree(skill.path, skills_out / skill.name)
            report.skills_written += 1

        # 3. instructions: split always-on vs narrow
        always_on: list[InstructionSource] = []
        narrow: list[InstructionSource] = []
        for ins in source.instructions:
            if ins.always_on:
                always_on.append(ins)
            else:
                narrow.append(ins)

        # global_rules.md: minimal directive only
        (memories_out / "global_rules.md").write_text(
            _GLOBAL_RULES_CONTENT, encoding="utf-8"
        )

        # agent-rules skill: all always-on instructions merged
        if always_on:
            merged_dir = skills_out / _MERGED_SKILL_NAME
            if merged_dir.exists():
                report.warnings.append(
                    f"name collision: native skill '{_MERGED_SKILL_NAME}' "
                    "conflicts with merged instructions skill"
                )
            else:
                merged_dir.mkdir(parents=True)
                (merged_dir / "SKILL.md").write_text(
                    _render_merged_skill(always_on), encoding="utf-8"
                )
                report.skills_written += 1
                report.instructions_written += len(always_on)

        # narrow-applyTo instructions: individual skills
        for ins in narrow:
            skill_name, skill_md = _render_instruction_skill(ins)
            skill_dir = skills_out / skill_name
            if skill_dir.exists():
                report.warnings.append(
                    f"name collision: '{skill_name}' already exists, skipping narrow instruction"
                )
            else:
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
                report.skills_written += 1
                report.instructions_written += 1

        # 4. prompts -> workflows (semantic 1:1)
        for prompt in source.prompts:
            shutil.copy2(
                prompt.path,
                workflows_out / f"{prompt.name}.md",
            )
            report.prompts_written += 1

        return report

    def install_targets(self) -> Iterable[InstallMapping]:
        root = "${USERPROFILE}/.codeium/windsurf"
        return (
            InstallMapping("memories", f"{root}/memories"),
            InstallMapping("skills", f"{root}/skills"),
            InstallMapping("global_workflows", f"{root}/global_workflows"),
        )


register(WindsurfAdapter())
