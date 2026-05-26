# Agentic Agent — 多平台 Agent/Skill 分发

单一事实源 -> 每平台适配器 -> 各自安装路径的一站式分发。

## 目录结构

```
Agentic-Agent/
├── source/                         # 唯一事实源（Copilot 原生格式）
│   ├── agents/*.agent.md
│   ├── skills/<name>/SKILL.md
│   ├── instructions/*.instructions.md
│   └── prompts/*.prompt.md
├── adapters/                       # 平台适配器
│   ├── base.py                     # PlatformAdapter 抽象基类 + 源加载
│   ├── copilot/
│   ├── codex/
│   ├── windsurf/
│   ├── opencode/
│   └── kimicode/
├── build/                          # 各平台生成产物（入库）
│   ├── _neutral_source/             # source 清洗后的中性中间层（生成）
│   ├── Copilot/
│   ├── Codex/
│   ├── Windsurf/
│   ├── OpenCode/
│   └── KimiCode/
├── scripts/
│   ├── build.py                    # source -> build/<Platform>/
│   └── distribute.py               # build/ -> 本机真实安装路径
└── docs/
    ├── codex-reference.md
    ├── windsurf-reference.md
    ├── opencode-reference.md
    └── kimicode-reference.md
```

## 常用命令

```bash
# 交互式引导：构建、预览分发目标、确认后安装
scripts/install-agent-config.sh

# 只预览交互式引导将写入哪些配置目录
scripts/install-agent-config.sh --dry-run

# 构建全部平台
python3 scripts/build.py

# 按 macOS profile 构建；会先生成 build/_neutral_source/
python3 scripts/build.py --platform macos

# 只扫描上游 source/ 中的系统相关痕迹
python3 scripts/build_platform.py --source source --scan-only

# 只构建 Codex
python3 scripts/build.py --target codex

# 预演分发（不写盘）
python3 scripts/distribute.py --dry-run

# 分发全部平台（默认先重建 build/）
python3 scripts/distribute.py

# 只分发 Copilot，不重建
python3 scripts/distribute.py --target copilot --no-build

# 合并模式（保留目的地其他文件）
python3 scripts/distribute.py --mode merge

# 额外安装到某个 repo 的项目级 Copilot 目录
python3 scripts/distribute.py --target copilot --copilot-project /path/to/repo
```

`build.py` 每次会清理对应的 `build/<Platform>/` 后重新生成，避免旧平台布局残留。`distribute.py` 默认会先执行同样的重建逻辑；传 `--no-build` 时只分发现有 build 产物。

## Source 转换流程

`source/` 被视为上游原始输入，不要求它跨平台中性，也不在构建中直接修改。当前上游内容可以保留 Windows / PowerShell / `.bat` / 个人路径等描述。

构建时走三段：

```text
source/
  -> build/_neutral_source/
  -> 临时 platform source
  -> build/<Platform>/
```

- `build/_neutral_source/`：由 `scripts/build_platform.py` 从 `source/` 生成，清洗平台痕迹并替换为占位符。
- 临时 platform source：根据 `--platform macos|linux|windows` 把占位符渲染成目标平台描述。
- `build/<Platform>/`：现有 adapters 只消费平台 source，不直接消费上游 `source/`。

默认 `--platform auto` 会按当前运行系统选择 profile。macOS 用户可显式使用：

```bash
python3 scripts/build.py --platform macos
python3 scripts/distribute.py --platform macos --dry-run
scripts/install-agent-config.sh --platform macos --dry-run
```

## macOS / Linux 分发目标

脚本会把 `${USERPROFILE}` 解析到 `$HOME`，所以 macOS 和 Linux 不走 `Library/Application Support` 作为 Copilot agents/skills 的默认位置。

| 平台 | build 产物 | 分发目标 |
|------|------------|----------|
| Copilot | `build/Copilot/agents` | `~/.copilot/agents` |
| Copilot | `build/Copilot/skills` | `~/.copilot/skills` |
| 通用 Agent Skills | `build/Copilot/skills` | `~/.agents/skills` |
| Copilot 项目级 agents | `build/Copilot/agents` | `<repo>/.github/agents` |
| Copilot 项目级 skills | `build/Copilot/skills` | `<repo>/.github/skills` |
| Codex | `build/Codex/.codex/agents` | `~/.codex/agents` |
| Codex | `build/Codex/.codex/AGENTS.md` | `~/.codex/AGENTS.md` |
| Codex | `build/Codex/.codex/skills` | `~/.codex/skills` |
| Windsurf | `build/Windsurf/memories` | `~/.codeium/windsurf/memories` |
| Windsurf | `build/Windsurf/skills` | `~/.codeium/windsurf/skills` |
| Windsurf | `build/Windsurf/global_workflows` | `~/.codeium/windsurf/global_workflows` |
| OpenCode | `build/OpenCode/AGENTS.md` | `~/.config/opencode/AGENTS.md` |
| OpenCode | `build/OpenCode/skills` | `~/.config/opencode/skills` |
| KimiCode | `build/KimiCode/skills` | `~/.kimi/skills` |

Copilot 个人级安装会优先写 `~/.copilot/agents` 和 `~/.copilot/skills`，并同步一份 skills 到 `~/.agents/skills`，方便其他支持 Agent Skills 标准的工具复用。项目级 Copilot 安装必须显式传 `--copilot-project <repo>`，不会默认写入当前仓库。

## Windows 分发目标

| 平台 | build 产物 | 分发目标 |
|------|------------|----------|
| Copilot | `build/Copilot/agents` | `%USERPROFILE%\.copilot\agents` |
| Copilot | `build/Copilot/skills` | `%USERPROFILE%\.copilot\skills` |
| 通用 Agent Skills | `build/Copilot/skills` | `%USERPROFILE%\.agents\skills` |
| Copilot 项目级 agents | `build/Copilot/agents` | `<repo>\.github\agents` |
| Copilot 项目级 skills | `build/Copilot/skills` | `<repo>\.github\skills` |
| Codex | `build/Codex/.codex/agents` | `%USERPROFILE%\.codex\agents` |
| Codex | `build/Codex/.codex/AGENTS.md` | `%USERPROFILE%\.codex\AGENTS.md` |
| Codex | `build/Codex/.codex/skills` | `%USERPROFILE%\.codex\skills` |
| Windsurf | `build/Windsurf/memories` | `%USERPROFILE%\.codeium\windsurf\memories` |
| Windsurf | `build/Windsurf/skills` | `%USERPROFILE%\.codeium\windsurf\skills` |
| Windsurf | `build/Windsurf/global_workflows` | `%USERPROFILE%\.codeium\windsurf\global_workflows` |
| OpenCode | `build/OpenCode/AGENTS.md` | `%USERPROFILE%\.config\opencode\AGENTS.md` |
| OpenCode | `build/OpenCode/skills` | `%USERPROFILE%\.config\opencode\skills` |
| KimiCode | `build/KimiCode/skills` | `%USERPROFILE%\.kimi\skills` |

## 平台适配规则

| 源内容 | Copilot | Codex | Windsurf | OpenCode | KimiCode |
|--------|---------|-------|----------|----------|----------|
| `source/agents/*.agent.md` | 原样复制 | 转为 `.codex/agents/*.toml` | 丢弃 | 丢弃 | 丢弃 |
| `source/skills/<name>/SKILL.md` | 原样复制 | 原样复制 | 原样复制 | 原样复制 | 原样复制 |
| `applyTo: "**"` instructions | 原样复制 | 合并到 `.codex/AGENTS.md` | 合并到 `agent-rules` skill | 合并到 `AGENTS.md` | 合并到 `agent-rules` skill |
| 窄范围 instructions | 原样复制 | 转成同名 skill | 转成同名 skill | 转成同名 skill | 转成同名 skill |
| `source/prompts/*.prompt.md` | 原样复制 | 丢弃 | 转为 global workflows | 丢弃 | 丢弃 |

## 源格式约定

- Agent：`source/agents/<name>.agent.md`，YAML frontmatter 必含 `description`；可选 `name`，不写则从文件名推断。
- Skill：`source/skills/<name>/SKILL.md` 加同目录任意资源，例如 `scripts/`、`references/`、`assets/`。
- Instruction：`source/instructions/*.instructions.md`，使用 Copilot 风格 frontmatter；`applyTo: "**"` 表示 always-on。
- Prompt：`source/prompts/*.prompt.md`，主要供 Copilot 和 Windsurf 使用。

## 分发模式

- `replace`（默认）：目的地子目录被完全替换，确保与 build 产物一致。
- `merge`：只覆盖同名文件，保留目的地其他内容。

## 新增平台

1. 在 `adapters/<name>/__init__.py` 实现 `PlatformAdapter` 子类。
2. 实现 `name`、`display_name`、`build(source, out_root)`、`install_targets()`。
3. 在 `adapters/__init__.py` import 新 adapter，让其自动注册。

每个适配器拥有自己独立的 formatter 逻辑，互不干扰。

## 设计约束

- 一切面向 build 产物，不直接改真实安装路径。
- 每次 build 幂等：目标平台目录先清再写。
- 平台专有字段由各自适配器决定保留或丢弃，不污染 `source/`。
