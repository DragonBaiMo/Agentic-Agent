"""Adapter registry. Import this to ensure all built-in adapters are registered."""
from .base import (  # noqa: F401
    AgentSource,
    BuildReport,
    InstallMapping,
    PlatformAdapter,
    SkillSource,
    SourceBundle,
    all_adapters,
    expand_path,
    get_adapter,
    load_source,
    register,
)

# register built-ins
from . import copilot as _copilot  # noqa: F401
from . import codex as _codex  # noqa: F401
from . import windsurf as _windsurf  # noqa: F401
