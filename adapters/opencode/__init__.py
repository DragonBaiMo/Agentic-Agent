"""OpenCode adapter.

Layout emitted under ``build/OpenCode/``::

    AGENTS.md                               # always-on instructions (applyTo **), concatenated
    skills/<name>/SKILL.md                  # native skills (passthrough) + narrow-applyTo instructions

Install targets (see docs/opencode-reference.md):
* ``AGENTS.md``   -> ``%USERPROFILE%\\.config\\opencode\\AGENTS.md``
* ``skills/``     -> ``%USERPROFILE%\\.config\\opencode\\skills``

Mapping rules:

* ``applyTo: "**"`` instructions -> concatenated into ``AGENTS.md`` (pure Markdown)
* narrow ``applyTo`` instructions -> individual ``skills/<name>/SKILL.md``
* ``source/skills/``             -> copied verbatim
* ``source/agents/``             -> dropped
* ``source/prompts/``            -> dropped
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


_AGENTS_MD_SEPARATOR = "\n\n---\n\n"


def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _render_agents_md(always_on: list[InstructionSource]) -> str:
    parts = [ins.body.strip() for ins in always_on]
    return _AGENTS_MD_SEPARATOR.join(parts) + "\n"


def _render_instruction_skill(ins: InstructionSource) -> tuple[str, str]:
    """Render a narrow-applyTo instruction as an OpenCode skill."""
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


class OpenCodeAdapter(PlatformAdapter):
    name = "opencode"
    display_name = "OpenCode"

    def build(self, source: SourceBundle, out_root: Path) -> BuildReport:
        report = BuildReport(platform=self.display_name, out_root=out_root)

        skills_out = out_root / "skills"
        agents_md_path = out_root / "AGENTS.md"

        clean_dir(skills_out)
        out_root.mkdir(parents=True, exist_ok=True)
        if agents_md_path.exists():
            agents_md_path.unlink()

        # 1. agents intentionally dropped
        if source.agents:
            report.warnings.append(
                f"{len(source.agents)} agent(s) dropped — OpenCode agent output is disabled"
            )

        # 2. native skills (copied as-is)
        for skill in source.skills:
            copy_skill_tree(skill.path, skills_out / skill.name)
            report.skills_written += 1

        # 3. instructions: always-on -> AGENTS.md, narrow -> individual skills
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

        # 4. prompts intentionally dropped
        if source.prompts:
            report.warnings.append(
                f"{len(source.prompts)} prompt(s) dropped — OpenCode prompt output is disabled"
            )

        return report

    def install_targets(self) -> Iterable[InstallMapping]:
        root = "${USERPROFILE}/.config/opencode"
        return (
            InstallMapping("AGENTS.md", f"{root}/AGENTS.md"),
            InstallMapping("skills", f"{root}/skills"),
        )


register(OpenCodeAdapter())
