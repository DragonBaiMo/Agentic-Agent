"""Scan, neutralize, and render source content for platform builds.

Pipeline:
    source/ -> build/_neutral_source/ -> temporary platform source -> build/<Platform>/

``source/`` is treated as upstream input. It may be Windows-specific and should
not be edited by this pipeline. ``build/_neutral_source/`` is generated from it
and replaces host-specific text with placeholders. The final platform source is
then rendered from those placeholders for macOS, Linux, or Windows.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {
    ".bat",
    ".cmd",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}

OS_SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("windows", re.compile(r"\bWindows\b", re.IGNORECASE)),
    ("powershell", re.compile(r"\bPowerShell\b|\bpwsh\b", re.IGNORECASE)),
    ("batch", re.compile(r"\.bat\b|cmd\.exe|cmd /", re.IGNORECASE)),
    ("windows_env", re.compile(r"%USERPROFILE%|%APPDATA%|\$\{USERPROFILE\}|\$\{APPDATA\}")),
    ("drive_path", re.compile(r"\b[A-Za-z]:\\[^\s`)]*")),
    ("user_path", re.compile(r"c:\\Users\\[^\\\s`]+", re.IGNORECASE)),
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    kind: str
    text: str


@dataclass
class SourceTransformReport:
    source_root: Path
    out_root: Path
    findings: list[Finding]
    rewrites: list[str]


def normalize_platform(value: str | None) -> str:
    raw = (value or sys.platform).lower()
    if raw == "auto":
        raw = sys.platform.lower()
    if raw.startswith("darwin") or raw in {"mac", "macos", "osx"}:
        return "macos"
    if raw.startswith("linux"):
        return "linux"
    if raw.startswith("win") or raw == "windows":
        return "windows"
    return raw


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {"AGENTS.md", "SKILL.md"}


def scan_source(source_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or not is_text_file(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, start=1):
            for kind, pattern in OS_SIGNAL_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            path=path.relative_to(source_root),
                            line=line_no,
                            kind=kind,
                            text=line.strip(),
                        )
                    )
                    break
    return findings


def print_scan(findings: list[Finding], limit: int = 120) -> None:
    if not findings:
        print("[platform-scan] no OS-specific signals found")
        return
    print(f"[platform-scan] OS-specific signals: {len(findings)}")
    for finding in findings[:limit]:
        print(
            f"  {finding.path}:{finding.line} [{finding.kind}] "
            f"{finding.text[:140]}"
        )
    if len(findings) > limit:
        print(f"  ... {len(findings) - limit} more")


def prepare_neutral_source(source_root: Path, neutral_root: Path) -> SourceTransformReport:
    """Generate the OS-neutral intermediate source tree."""
    _fresh_copytree(source_root, neutral_root)

    source_findings = scan_source(source_root)
    rewrites: list[str] = []

    _neutralize_agents_instruction(neutral_root, rewrites)
    _neutralize_development_environment(neutral_root, rewrites)
    _neutralize_one_click_scripts(neutral_root, rewrites)
    _neutralize_dev_orchestration(neutral_root, rewrites)
    _neutralize_git_master(neutral_root, rewrites)
    _neutralize_playwright(neutral_root, rewrites)
    _neutralize_small_mentions(neutral_root, rewrites)

    return SourceTransformReport(
        source_root=source_root,
        out_root=neutral_root,
        findings=source_findings,
        rewrites=rewrites,
    )


def prepare_platform_source(
    neutral_root: Path,
    out_root: Path,
    platform: str | None = None,
) -> SourceTransformReport:
    """Render a platform-specific source tree from the neutral tree."""
    target = normalize_platform(platform)
    profile = PLATFORM_PROFILES[target]

    if out_root.exists():
        _remove_tree(out_root)
    shutil.copytree(neutral_root, out_root)

    rewrites: list[str] = []
    for path in sorted(out_root.rglob("*")):
        if not path.is_file() or not is_text_file(path):
            continue
        text = _read(path)
        rendered = _render_placeholders(text, profile)
        if rendered != text:
            _write(path, rendered, rewrites)

    _render_dev_orchestration_launcher(out_root, target, rewrites)

    return SourceTransformReport(
        source_root=neutral_root,
        out_root=out_root,
        findings=scan_source(neutral_root),
        rewrites=rewrites,
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _remove_tree(path: Path) -> None:
    def _chmod_and_retry(func, target, exc_info):
        try:
            os.chmod(target, 0o700)
            func(target)
        except Exception:
            raise exc_info[1]

    if path.exists():
        shutil.rmtree(path, onexc=_chmod_and_retry)


def _fresh_copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        stale = dst.with_name(dst.name + ".stale")
        if stale.exists():
            _remove_tree(stale)
        dst.rename(stale)
        try:
            _remove_tree(stale)
        except OSError:
            # The target path is already free for a clean copy. A stale folder
            # can be cleaned manually if macOS keeps a transient handle open.
            pass
    shutil.copytree(src, dst)


def _write(path: Path, text: str, rewrites: list[str]) -> None:
    path.write_text(text, encoding="utf-8")
    rewrites.append(str(path))


def _replace_file(path: Path, text: str, rewrites: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path, text, rewrites)


def _render_placeholders(text: str, profile: dict[str, str]) -> str:
    rendered = text
    for key, value in profile.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def _neutralize_agents_instruction(root: Path, rewrites: list[str]) -> None:
    path = root / "instructions" / "AGENTS.md.instructions.md"
    if not path.exists():
        return
    text = _read(path)
    replacements = {
        "- 默认：Windows 11 PowerShell（UTF-8）": "- 默认：{{DEFAULT_SHELL}}",
        "- 多命令串接：`;`，禁用 `&&`": "- 多命令串接：{{COMMAND_CHAINING}}",
        "- 路径：Windows 风格（`C:\\...` / `C:\\\\...`），不假设 Linux-only 路径": "- 路径：{{PATH_STYLE}}",
        "- `.bat` / `.ps1` 脚本执行或编码出问题 → 优先考虑 Nodejs / Python 包装": "- {{SCRIPT_TROUBLESHOOTING}}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    _write(path, text, rewrites)


def _neutralize_development_environment(root: Path, rewrites: list[str]) -> None:
    path = root / "instructions" / "development-environment.instructions.md"
    if not path.exists():
        return
    _replace_file(
        path,
        "---\n"
        "description: Development environment for AI agents.\n"
        'applyTo: "**"\n'
        "---\n"
        "{{DEVELOPMENT_ENVIRONMENT_BODY}}\n",
        rewrites,
    )


def _neutralize_one_click_scripts(root: Path, rewrites: list[str]) -> None:
    skill_dir = root / "skills" / "one-click-scripts"
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return
    _replace_file(skill_md, "{{ONE_CLICK_SCRIPTS_SKILL}}\n", rewrites)

    references = skill_dir / "references"
    if references.exists():
        shutil.rmtree(references)
        rewrites.append(str(references))
    references.mkdir(parents=True, exist_ok=True)
    _replace_file(
        references / "tech-patterns.md",
        "{{ONE_CLICK_SCRIPTS_TECH_PATTERNS}}\n",
        rewrites,
    )


def _neutralize_dev_orchestration(root: Path, rewrites: list[str]) -> None:
    skill_dir = root / "skills" / "dev-orchestration"
    if not skill_dir.exists():
        return

    bat = skill_dir / "dev-orch.bat"
    if bat.exists():
        bat.unlink()
        rewrites.append(str(bat))

    for path in sorted((skill_dir / "data" / "templates").glob("*.md*")):
        text = _read(path)
        text = re.sub(
            r"c:\\Users\\Dragon\\.copilot\\skills\\ai-testing-workflow\\references",
            "{{AI_TESTING_WORKFLOW_REFERENCES_ROOT}}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"c:\\Users\\Dragon\\.copilot\\skills\\ai-testing-workflow\\SKILL\.md",
            "{{AI_TESTING_WORKFLOW_SKILL_MD}}",
            text,
            flags=re.IGNORECASE,
        )
        _write(path, text, rewrites)


def _neutralize_small_mentions(root: Path, rewrites: list[str]) -> None:
    replacements = {
        "PowerShell/Python HTTP 请求": "{{HTTP_DOWNLOAD_METHOD}}",
        "execute（PowerShell/Python HTTP 请求，不手动拼字符串写文件）": "execute（{{HTTP_DOWNLOAD_METHOD}}，不手动拼字符串写文件）",
        "当前工作目录`.\\askquestions\\···`": "当前工作目录`{{ASKQUESTIONS_PATH}}`",
        "生成唯一 run-id（Windows 友好，无冒号）。": "生成唯一 run-id（跨平台友好，无冒号）。",
    }
    for rel in (
        Path("agents/librarian.agent.md"),
        Path("skills/ask-others/SKILL.md"),
        Path("skills/dev-orchestration/scripts/state.py"),
    ):
        path = root / rel
        if not path.exists():
            continue
        text = _read(path)
        new_text = text
        for old, new in replacements.items():
            new_text = new_text.replace(old, new)
        if new_text != text:
            _write(path, new_text, rewrites)


def _neutralize_git_master(root: Path, rewrites: list[str]) -> None:
    path = root / "skills" / "git-master" / "SKILL.md"
    if not path.exists():
        return
    _replace_file(path, "{{GIT_MASTER_SKILL}}\n", rewrites)


def _neutralize_playwright(root: Path, rewrites: list[str]) -> None:
    path = root / "skills" / "playwright" / "SKILL.md"
    if not path.exists():
        return
    text = _read(path)
    text = text.replace(
        "Windows: use `npx playwright test` — no `./node_modules/.bin` prefix needed.",
        "{{PLAYWRIGHT_LOCAL_COMMAND_NOTE}}",
    )
    text = text.replace(
        "GitHub Actions (Windows runner):",
        "GitHub Actions ({{PLAYWRIGHT_CI_RUNNER}}):",
    )
    _write(path, text, rewrites)


def _render_dev_orchestration_launcher(root: Path, platform: str, rewrites: list[str]) -> None:
    skill_dir = root / "skills" / "dev-orchestration"
    if not skill_dir.exists():
        return
    if platform == "windows":
        _replace_file(
            skill_dir / "dev-orch.bat",
            "@echo off\r\npython \"%~dp0scripts\\cli.py\" %*\r\n",
            rewrites,
        )
    else:
        _replace_file(
            skill_dir / "dev-orch.sh",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
            'python3 "$SCRIPT_DIR/scripts/cli.py" "$@"\n',
            rewrites,
        )


def _development_environment_body(platform_label: str) -> str:
    return f"""# AI 开发环境说明

默认 shell：{platform_label}。裸命令优先；命令不存在时先探测 PATH 和项目文档，不假设原作者本机私有工具目录存在。

## 平台约定

- Home 目录：`$HOME` / `~`
- 路径风格：POSIX 路径，例如 `~/project`、`./src`、`/usr/local/bin`
- 脚本优先级：`.sh`、Python、Node.js；不要默认生成非 POSIX 脚本
- 多命令执行：优先拆成独立命令；确需串接时遵循 POSIX shell 语义
- 不写入 Token / 密码等 secrets 到脚本默认值或文档示例

## 运行时 / 构建

按项目实际信号文件和本机 PATH 探测工具，不假设固定版本或绝对安装目录：

- Python：`python3` / `pip3` / `uv`
- Node.js：`node` / `npm` / `pnpm` / `yarn` / `bun`
- Java：`java` / `javac` / `mvn` / `gradle`
- Go：`go`
- Rust：`cargo` / `rustc`
- .NET：`dotnet`
- C/C++：`clang` / `gcc` / `cmake`

## 数据库客户端

不要假设本机固定账号密码。根据项目 `.env.example`、compose 文件、README 或迁移配置确认 `mysql`、`psql`、`redis-cli`、`sqlite3` 等工具。

## 浏览器自动化

GUI / 浏览器自动化启动前记录 PID、端口或会话标识；任务结束时关闭本次启动的资源。
"""


def _one_click_scripts_skill(platform_label: str) -> str:
    return f"""---
name: one-click-scripts
description: >
  为任意项目生成 POSIX shell 一键脚本，面向 {platform_label}。
  自动识别技术栈，生成可从终端运行的 .sh 文件。
  触发词："一键启动"、"生成启动脚本"、"一键导入"、"一键重置"、"写个 start.sh"、"shell 脚本"。
---

# One-Click Scripts —— POSIX 一键脚本生成

目标平台：{platform_label}。

为项目生成三个可运行的 `.sh` 脚本，职责分离：

| 脚本 | 职责 |
|------|------|
| `setup.sh` | 创建环境、安装依赖、必要时编译 |
| `start.sh` | 启动服务，假设环境已就绪 |
| `reimport.sh` | 清空数据库并重新初始化导入 |

## 固定约束

- 第一行使用 `#!/usr/bin/env bash`
- 使用 `set -euo pipefail`
- 文件编码 UTF-8，无 BOM，行尾 LF
- 生成后提示 `chmod +x setup.sh start.sh reimport.sh`
- 用脚本目录定位项目根，不硬编码绝对路径
- 危险数据操作必须二次确认
- `start.sh` 不安装依赖、不创建环境
- 多服务项目拆出服务级脚本，根脚本负责编排
"""


def _one_click_scripts_tech_patterns(platform_label: str) -> str:
    return f"""# One-Click Scripts Tech Patterns

目标平台：{platform_label} / POSIX shell。

## Python

- 创建环境：`python3 -m venv .venv`
- 安装依赖：`.venv/bin/pip install -r requirements.txt`
- 运行：`.venv/bin/python app.py`

## Node.js

- 优先按 lockfile 选择 `pnpm install`、`yarn install` 或 `npm install`
- 启动脚本优先读取 `package.json` 的 `scripts`

## 端口检查

- 检查端口：`lsof -ti :<port>`
- 只终止确认属于本项目的进程，禁止一刀切杀运行时进程。
"""


def _git_master_skill(platform_label: str, shell_label: str) -> str:
    return f"""---
name: git-master
description: >
  Git workflow guidance for {platform_label}: inspect history, manage branches,
  review changes, resolve conflicts, and keep commits intentional.
---

# Git Master

默认 shell：{shell_label}。

## 基本原则

- 修改前先看 `git status --short --branch`
- 提交前用 `git diff` 和 `git diff --staged` 审查
- 不重置或覆盖用户未确认的改动
- 处理冲突时先理解双方变更，再决定保留、合并或重写

## 常用命令

```bash
git status --short --branch
git diff
git diff --staged
git log --oneline --decorate -n 20
git branch --show-current
```

## 提交

```bash
git add <paths>
git commit -m "type(scope): summary"
```

## 排查历史

```bash
git log --oneline -- <path>
git blame -- <path>
git show <commit>
```
"""


def _windows_development_environment_body() -> str:
    return """# AI 开发环境说明

默认 shell：PowerShell / pwsh（UTF-8）。裸命令优先；命令不存在时先用 `Get-Command <tool>` 或项目文档确认安装方式，不假设原作者本机固定盘符或私有工具目录存在。

## 平台约定

- Home 目录：`%USERPROFILE%`
- 路径风格：Windows 路径，例如 `%USERPROFILE%\\project`、`.\\src`
- 脚本优先级：`.bat`、`.ps1`、Python、Node.js
- 多命令执行：优先拆成独立命令；PowerShell 中可用 `;`
- 不写入 Token / 密码等 secrets 到脚本默认值或文档示例
"""


WINDOWS_ONE_CLICK_SCRIPTS = """---
name: one-click-scripts
description: >
  为任意项目生成 Windows 一键脚本。
  自动识别技术栈，生成 .bat 或 .ps1 文件。
---

# One-Click Scripts —— Windows 一键脚本生成

默认生成 `setup.bat`、`start.bat`、`reimport.bat`，职责分离。路径用 `%~dp0` 定位脚本所在目录，禁止硬编码绝对路径；危险数据操作必须二次确认。
"""


PLATFORM_PROFILES: dict[str, dict[str, str]] = {
    "macos": {
        "DEFAULT_SHELL": "macOS zsh/bash（UTF-8）",
        "COMMAND_CHAINING": "优先拆分为独立命令；确需串接时使用 POSIX shell 语义",
        "PATH_STYLE": "POSIX 风格（`/Users/...`、`~/...`、`./...`），不假设其他平台专用路径",
        "SCRIPT_TROUBLESHOOTING": "shell 脚本执行或权限出问题 -> 优先检查 shebang、可执行权限和 POSIX 兼容性；跨平台场景优先考虑 Node.js / Python 包装",
        "DEVELOPMENT_ENVIRONMENT_BODY": _development_environment_body("macOS zsh/bash"),
        "ONE_CLICK_SCRIPTS_SKILL": _one_click_scripts_skill("macOS"),
        "ONE_CLICK_SCRIPTS_TECH_PATTERNS": _one_click_scripts_tech_patterns("macOS"),
        "GIT_MASTER_SKILL": _git_master_skill("macOS", "zsh/bash"),
        "PLAYWRIGHT_LOCAL_COMMAND_NOTE": "macOS/Linux: use `npx playwright test`; avoid hardcoding `./node_modules/.bin` unless the project requires it.",
        "PLAYWRIGHT_CI_RUNNER": "macOS/Linux runner",
        "AI_TESTING_WORKFLOW_REFERENCES_ROOT": "~/.copilot/skills/ai-testing-workflow/references",
        "AI_TESTING_WORKFLOW_SKILL_MD": "~/.copilot/skills/ai-testing-workflow/SKILL.md",
        "HTTP_DOWNLOAD_METHOD": "curl/Python HTTP 请求",
        "ASKQUESTIONS_PATH": "./askquestions/...",
    },
    "linux": {
        "DEFAULT_SHELL": "Linux bash/zsh（UTF-8）",
        "COMMAND_CHAINING": "优先拆分为独立命令；确需串接时使用 POSIX shell 语义",
        "PATH_STYLE": "POSIX 风格（`/home/...`、`~/...`、`./...`），不假设其他平台专用路径",
        "SCRIPT_TROUBLESHOOTING": "shell 脚本执行或权限出问题 -> 优先检查 shebang、可执行权限和 POSIX 兼容性；跨平台场景优先考虑 Node.js / Python 包装",
        "DEVELOPMENT_ENVIRONMENT_BODY": _development_environment_body("Linux bash/zsh"),
        "ONE_CLICK_SCRIPTS_SKILL": _one_click_scripts_skill("Linux"),
        "ONE_CLICK_SCRIPTS_TECH_PATTERNS": _one_click_scripts_tech_patterns("Linux"),
        "GIT_MASTER_SKILL": _git_master_skill("Linux", "bash/zsh"),
        "PLAYWRIGHT_LOCAL_COMMAND_NOTE": "Linux: use `npx playwright test`; install required system dependencies before browser tests.",
        "PLAYWRIGHT_CI_RUNNER": "Linux runner",
        "AI_TESTING_WORKFLOW_REFERENCES_ROOT": "~/.copilot/skills/ai-testing-workflow/references",
        "AI_TESTING_WORKFLOW_SKILL_MD": "~/.copilot/skills/ai-testing-workflow/SKILL.md",
        "HTTP_DOWNLOAD_METHOD": "curl/Python HTTP 请求",
        "ASKQUESTIONS_PATH": "./askquestions/...",
    },
    "windows": {
        "DEFAULT_SHELL": "Windows PowerShell / pwsh（UTF-8）",
        "COMMAND_CHAINING": "优先拆分为独立命令；PowerShell 中可用 `;`",
        "PATH_STYLE": "Windows 风格（`%USERPROFILE%\\...`、`.\\...`），不假设 POSIX-only 路径",
        "SCRIPT_TROUBLESHOOTING": "批处理或 PowerShell 脚本执行出问题 -> 优先检查编码、行尾和执行策略；跨平台场景优先考虑 Node.js / Python 包装",
        "DEVELOPMENT_ENVIRONMENT_BODY": _windows_development_environment_body(),
        "ONE_CLICK_SCRIPTS_SKILL": WINDOWS_ONE_CLICK_SCRIPTS,
        "ONE_CLICK_SCRIPTS_TECH_PATTERNS": "按项目技术栈生成 Windows 脚本模式；路径使用 `%~dp0`，避免硬编码绝对路径。\n",
        "GIT_MASTER_SKILL": _git_master_skill("Windows", "PowerShell / pwsh"),
        "PLAYWRIGHT_LOCAL_COMMAND_NOTE": "Windows: use `npx playwright test` — no `./node_modules/.bin` prefix needed.",
        "PLAYWRIGHT_CI_RUNNER": "Windows runner",
        "AI_TESTING_WORKFLOW_REFERENCES_ROOT": "%USERPROFILE%\\.copilot\\skills\\ai-testing-workflow\\references",
        "AI_TESTING_WORKFLOW_SKILL_MD": "%USERPROFILE%\\.copilot\\skills\\ai-testing-workflow\\SKILL.md",
        "HTTP_DOWNLOAD_METHOD": "PowerShell/Python HTTP 请求",
        "ASKQUESTIONS_PATH": ".\\askquestions\\...",
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan, neutralize, or render source content.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--neutral-out", type=Path)
    parser.add_argument("--platform-out", type=Path)
    parser.add_argument("--platform", default="auto", choices=("auto", "macos", "linux", "windows"))
    parser.add_argument("--scan-only", action="store_true")
    parser.add_argument("--scan-limit", type=int, default=120)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.source.is_dir():
        print(f"[error] source not found: {args.source}", file=sys.stderr)
        return 2

    findings = scan_source(args.source)
    print_scan(findings, args.scan_limit)
    if args.scan_only:
        return 0

    if args.neutral_out is None:
        print("[error] --neutral-out is required unless --scan-only is used", file=sys.stderr)
        return 2

    neutral_report = prepare_neutral_source(args.source, args.neutral_out)
    print(
        f"[neutral-source] rewrites={len(neutral_report.rewrites)} "
        f"source-signals={len(neutral_report.findings)} -> {neutral_report.out_root}"
    )

    if args.platform_out is not None:
        platform_report = prepare_platform_source(
            args.neutral_out,
            args.platform_out,
            args.platform,
        )
        print(
            f"[platform-source] platform={normalize_platform(args.platform)} "
            f"rewrites={len(platform_report.rewrites)} -> {platform_report.out_root}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
