"""Kimi Code adapter.

Layout emitted under ``build/KimiCode/``::

    skills/agent-rules/SKILL.md     # merged: all always-on instructions (applyTo **)
    skills/<name>/SKILL.md          # individual skills for narrow-applyTo instructions
    skills/<native>/                 # native skills from source/skills (passthrough)

Install targets (see docs/kimicode-reference.md):
* ``skills/`` -> ``%USERPROFILE%\\.kimi\\skills``

Mapping rules:

* ``source/agents/``       -> dropped. Kimi has no auto-discovery agent dir;
                              custom agents require --agent-file (YAML format).
* ``applyTo: "**"`` instructions -> merged into ``agent-rules/SKILL.md``.
* narrow ``applyTo`` instructions -> individual ``skills/<name>/SKILL.md``.
* ``source/skills/``       -> copied verbatim (SKILL.md format is identical).
* ``source/prompts/``      -> dropped. Kimi has no slash-command mechanism.

Kimi Code has no user-level global AGENTS.md equivalent, so always-on
instructions follow the same mandatory-skill pattern as Windsurf.
"""
from __future__ import annotations

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
    "sql), UI design."
)

_SECTION_SEPARATOR = "\n\n---\n\n"


def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _render_merged_skill(always_on: list[InstructionSource]) -> str:
    front = (
        "---\n"
        f"name: {_MERGED_SKILL_NAME}\n"
        f'description: "{_yaml_escape(_MERGED_SKILL_DESCRIPTION)}"\n'
        "---\n\n"
    )
    sections = [ins.body.strip() for ins in always_on]
    return front + _SECTION_SEPARATOR.join(sections) + "\n"


def _render_instruction_skill(ins: InstructionSource) -> tuple[str, str]:
    skill_name = ins.name
    trigger_hint = f"Use when editing files matching: {ins.apply_to}" if ins.apply_to else ""
    desc = ins.description.strip()
    if trigger_hint and trigger_hint not in desc:
        desc = f"{desc} {trigger_hint}".strip()
    desc_safe = _yaml_escape(desc)
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


class KimiCodeAdapter(PlatformAdapter):
    name = "kimicode"
    display_name = "KimiCode"

    def build(self, source: SourceBundle, out_root: Path) -> BuildReport:
        report = BuildReport(platform=self.display_name, out_root=out_root)

        skills_out = out_root / "skills"
        clean_dir(skills_out)

        # 1. agents: dropped
        if source.agents:
            report.warnings.append(
                f"{len(source.agents)} agent(s) dropped — "
                "Kimi Code has no auto-discovery agent dir; use --agent-file (YAML) instead"
            )

        # 2. native skills: direct copy
        for skill in source.skills:
            copy_skill_tree(skill.path, skills_out / skill.name)
            report.skills_written += 1

        # 3. instructions: always-on -> agent-rules, narrow -> individual skills
        always_on: list[InstructionSource] = []
        narrow: list[InstructionSource] = []
        for ins in source.instructions:
            (always_on if ins.always_on else narrow).append(ins)

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

        # 4. prompts: dropped
        if source.prompts:
            report.warnings.append(
                f"{len(source.prompts)} prompt(s) dropped — Kimi Code has no slash-command mechanism"
            )

        return report

    def install_targets(self) -> Iterable[InstallMapping]:
        return (
            InstallMapping("skills", "${USERPROFILE}/.kimi/skills"),
        )


register(KimiCodeAdapter())
