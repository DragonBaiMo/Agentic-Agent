"""Copilot adapter: passthrough.

Copilot consumes the source format natively. Build step copies ``agents/``,
``skills/``, ``instructions/``, and ``prompts/`` unchanged into
``build/Copilot/``.

Install targets mirror the VS Code Copilot layout:
* ``agents/``       -> ``%USERPROFILE%\\.copilot\\agents``
* ``skills/``       -> ``%USERPROFILE%\\.copilot\\skills``
* ``instructions/`` -> ``%USERPROFILE%\\.copilot\\instructions``
* ``prompts/``      -> ``%APPDATA%\\Code\\User\\prompts``
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from ..base import (
    BuildReport,
    InstallMapping,
    PlatformAdapter,
    SourceBundle,
    clean_dir,
    copy_skill_tree,
    register,
)


class CopilotAdapter(PlatformAdapter):
    name = "copilot"
    display_name = "Copilot"

    def build(self, source: SourceBundle, out_root: Path) -> BuildReport:
        report = BuildReport(platform=self.display_name, out_root=out_root)

        agents_out = out_root / "agents"
        skills_out = out_root / "skills"
        instructions_out = out_root / "instructions"
        prompts_out = out_root / "prompts"
        clean_dir(agents_out)
        clean_dir(skills_out)
        clean_dir(instructions_out)
        clean_dir(prompts_out)

        for agent in source.agents:
            shutil.copy2(agent.path, agents_out / agent.path.name)
            report.agents_written += 1

        for skill in source.skills:
            copy_skill_tree(skill.path, skills_out / skill.name)
            report.skills_written += 1

        # instructions: mirror the entire tree so ``references/`` etc. follow
        src_ins_root = self._instructions_root(source)
        if src_ins_root is not None:
            for item in src_ins_root.iterdir():
                target = instructions_out / item.name
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            report.instructions_written = sum(
                1 for _ in instructions_out.rglob("*.md")
            )

        for prompt in source.prompts:
            shutil.copy2(prompt.path, prompts_out / prompt.path.name)
            report.prompts_written += 1

        return report

    @staticmethod
    def _instructions_root(source: SourceBundle) -> Path | None:
        if not source.instructions:
            return None
        # all instructions come from the same directory
        return source.instructions[0].path.parent

    def install_targets(self) -> Iterable[InstallMapping]:
        return (
            InstallMapping("agents", "${USERPROFILE}/.copilot/agents"),
            InstallMapping("skills", "${USERPROFILE}/.copilot/skills"),
            InstallMapping("instructions", "${USERPROFILE}/.copilot/instructions"),
            InstallMapping("prompts", "${APPDATA}/Code/User/prompts"),
        )


register(CopilotAdapter())
