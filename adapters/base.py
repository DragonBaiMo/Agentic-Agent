"""Adapter framework for multi-platform agent/skill distribution.

Source of truth: ``source/`` (Copilot-native format: ``*.agent.md`` with YAML
frontmatter; skills as directories with ``SKILL.md``).

Each platform ships an adapter implementing ``PlatformAdapter``:

* ``build(src, out)`` — emit platform-native files under ``build/<Name>/``.
* ``install_targets()`` — declare where built artifacts map on the local
  machine for distribution.

New platforms (Claude, Windsurf, ...) plug in by subclassing and registering.
"""
from __future__ import annotations

import os
import re
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Source model


@dataclass(frozen=True)
class AgentSource:
    """A canonical agent definition parsed from ``source/agents/*.agent.md``.

    ``frontmatter_raw`` is kept as the original YAML block text so adapters
    that need specific keys can re-parse it without loss.
    """

    path: Path
    name: str
    description: str
    frontmatter_raw: str
    body: str


@dataclass(frozen=True)
class SkillSource:
    path: Path  # directory containing SKILL.md
    name: str


@dataclass(frozen=True)
class InstructionSource:
    """A Copilot-style instruction file with YAML frontmatter.

    ``apply_to`` is the raw ``applyTo`` value (may be ``"**"`` for always-on,
    or a comma-separated glob list). ``always_on`` is a derived convenience.
    """

    path: Path
    name: str           # stem without ``.instructions.md``
    description: str
    apply_to: str       # raw applyTo value, empty string if absent
    frontmatter_raw: str
    body: str

    @property
    def always_on(self) -> bool:
        return self.apply_to.strip() in ("", "**", "*")


@dataclass(frozen=True)
class PromptSource:
    path: Path
    name: str           # stem without ``.prompt.md``


@dataclass(frozen=True)
class SourceBundle:
    agents: tuple[AgentSource, ...]
    skills: tuple[SkillSource, ...]
    instructions: tuple[InstructionSource, ...] = ()
    prompts: tuple[PromptSource, ...] = ()


@dataclass
class BuildReport:
    platform: str
    out_root: Path
    agents_written: int = 0
    skills_written: int = 0
    instructions_written: int = 0
    prompts_written: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"[{self.platform}] agents={self.agents_written} "
            f"skills={self.skills_written} "
            f"instructions={self.instructions_written} "
            f"prompts={self.prompts_written} -> {self.out_root}"
        )


@dataclass(frozen=True)
class InstallMapping:
    """Declares ``src -> dst`` for distribution.

    ``src`` is relative to the platform's ``build/<Platform>/`` root.
    ``dst`` is an absolute path with ``$env:USERPROFILE`` / ``%USERPROFILE%``
    allowed for portability; the distributor expands them.
    """

    src_subpath: str
    dst_path: str  # may contain ${USERPROFILE} / $HOME placeholders


# ---------------------------------------------------------------------------
# Source loading

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
_SCALAR_RE_CACHE: dict[str, re.Pattern[str]] = {}


def split_frontmatter(text: str) -> tuple[str, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), m.group(2)


def extract_scalar(frontmatter: str, key: str) -> str | None:
    """Best-effort YAML scalar extraction (no full YAML dependency).

    Handles ``key: value``, ``key: "value"``, ``key: 'value'`` at line start.
    Not a YAML parser; list/object values return None intentionally.
    """
    pattern = _SCALAR_RE_CACHE.get(key)
    if pattern is None:
        pattern = re.compile(
            rf"^{re.escape(key)}\s*:\s*(.+?)\s*$", re.MULTILINE
        )
        _SCALAR_RE_CACHE[key] = pattern
    m = pattern.search(frontmatter)
    if not m:
        return None
    raw = m.group(1).strip()
    # reject list/object openings
    if raw.startswith("[") or raw.startswith("{") or raw.startswith("|") or raw.startswith(">"):
        return None
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        raw = raw[1:-1]
    return raw


def load_agent(path: Path) -> AgentSource:
    raw = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(raw)

    name = extract_scalar(fm, "name")
    if not name:
        stem = path.stem
        if stem.endswith(".agent"):
            stem = stem[: -len(".agent")]
        name = stem
    description = extract_scalar(fm, "description") or ""

    return AgentSource(
        path=path,
        name=name,
        description=description,
        frontmatter_raw=fm,
        body=body,
    )


def load_skill(path: Path) -> SkillSource:
    return SkillSource(path=path, name=path.name)


_INSTRUCTIONS_SUFFIX = ".instructions.md"
_PROMPT_SUFFIX = ".prompt.md"


def load_instruction(path: Path) -> InstructionSource:
    raw = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(raw)
    name = path.name
    if name.endswith(_INSTRUCTIONS_SUFFIX):
        name = name[: -len(_INSTRUCTIONS_SUFFIX)]
    else:
        name = path.stem
    description = extract_scalar(fm, "description") or ""
    apply_to = extract_scalar(fm, "applyTo") or ""
    return InstructionSource(
        path=path,
        name=name,
        description=description,
        apply_to=apply_to,
        frontmatter_raw=fm,
        body=body,
    )


def load_prompt(path: Path) -> PromptSource:
    name = path.name
    if name.endswith(_PROMPT_SUFFIX):
        name = name[: -len(_PROMPT_SUFFIX)]
    else:
        name = path.stem
    return PromptSource(path=path, name=name)


def load_source(src_root: Path) -> SourceBundle:
    agents_dir = src_root / "agents"
    skills_dir = src_root / "skills"
    instructions_dir = src_root / "instructions"
    prompts_dir = src_root / "prompts"

    agents: list[AgentSource] = []
    if agents_dir.is_dir():
        for p in sorted(agents_dir.glob("*.agent.md")):
            agents.append(load_agent(p))

    skills: list[SkillSource] = []
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                skills.append(load_skill(entry))

    instructions: list[InstructionSource] = []
    if instructions_dir.is_dir():
        for p in sorted(instructions_dir.glob("*.instructions.md")):
            instructions.append(load_instruction(p))
        # accept bare .md for legacy files sitting directly in instructions/
        for p in sorted(instructions_dir.glob("*.md")):
            if p.name.endswith(_INSTRUCTIONS_SUFFIX):
                continue
            instructions.append(load_instruction(p))

    prompts: list[PromptSource] = []
    if prompts_dir.is_dir():
        for p in sorted(prompts_dir.glob("*.prompt.md")):
            prompts.append(load_prompt(p))

    return SourceBundle(
        agents=tuple(agents),
        skills=tuple(skills),
        instructions=tuple(instructions),
        prompts=tuple(prompts),
    )


# ---------------------------------------------------------------------------
# Adapter base


class PlatformAdapter(ABC):
    """Base class for per-platform builders.

    Subclasses implement ``build()`` to emit native files under ``out_root``
    and ``install_targets()`` to declare distribution destinations.
    """

    #: short, filesystem-safe identifier ("copilot", "codex", "claude", ...)
    name: str = ""
    #: human-readable label used for build/<Label>/ directory
    display_name: str = ""

    @abstractmethod
    def build(self, source: SourceBundle, out_root: Path) -> BuildReport:
        raise NotImplementedError

    @abstractmethod
    def install_targets(self) -> Iterable[InstallMapping]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helpers shared by adapters


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_skill_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def expand_path(template: str) -> Path:
    """Expand ``${USERPROFILE}`` / ``$HOME`` / ``~`` in a path template."""
    # normalize windows-style
    s = template.replace("%USERPROFILE%", "${USERPROFILE}")
    s = os.path.expandvars(s)
    s = os.path.expanduser(s)
    return Path(s)


# ---------------------------------------------------------------------------
# Registry


_REGISTRY: dict[str, PlatformAdapter] = {}


def register(adapter: PlatformAdapter) -> PlatformAdapter:
    if not adapter.name:
        raise ValueError("adapter.name must be set")
    _REGISTRY[adapter.name] = adapter
    return adapter


def get_adapter(name: str) -> PlatformAdapter:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise KeyError(
            f"unknown platform '{name}'. registered: {sorted(_REGISTRY)}"
        ) from exc


def all_adapters() -> list[PlatformAdapter]:
    return list(_REGISTRY.values())
