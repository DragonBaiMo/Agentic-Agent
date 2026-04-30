# 0. OpenCode 全局配置根目录

Windows：

```txt
%USERPROFILE%\.config\opencode\
```

等价：

```txt
C:\Users\你的用户名\.config\opencode\
```

macOS / Linux：

```txt
~/.config/opencode/
```

OpenCode 官方主配置是 JSON / JSONC，配置会按层级合并，不是整文件替换。加载顺序大致是：remote config → global config → `OPENCODE_CONFIG` → project `opencode.json` → `.opencode/` 目录 → `OPENCODE_CONFIG_CONTENT` → managed config。后面的覆盖前面的，终于有个工具没把配置优先级写成玄学祭坛。([OpenCode][2])

---

# 1. 全局主配置：`opencode.json / opencode.jsonc`

路径：

```txt
%USERPROFILE%\.config\opencode\opencode.json
%USERPROFILE%\.config\opencode\opencode.jsonc
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode -Force
notepad $env:USERPROFILE\.config\opencode\opencode.jsonc
```

可用顶层键：

```txt
$schema
server
tools
provider
model
small_model
agent
default_agent
share
command
snapshot
autoupdate
formatter
permission
compaction
watcher
mcp
plugin
instructions
disabled_providers
enabled_providers
experimental
```

常见值类型：

```txt
$schema = "https://opencode.ai/config.json"

model = string，例如 "anthropic/claude-sonnet-4-5"
small_model = string

provider = object
agent = object
command = object
mcp = object
plugin = array<string>
instructions = array<string>
disabled_providers = array<string>
enabled_providers = array<string>

snapshot = boolean
autoupdate = boolean | "notify"
share = "manual" | "auto" | "disabled"
```

OpenCode 官方配置页明确列出这些主配置项：server、tools、models、agents、default_agent、sharing、commands、snapshot、autoupdate、formatters、permissions、compaction、watcher、MCP、plugins、instructions、provider allow/deny 等。([OpenCode][2])

---

# 2. TUI 配置：`tui.json / tui.jsonc`

路径：

```txt
%USERPROFILE%\.config\opencode\tui.json
%USERPROFILE%\.config\opencode\tui.jsonc
```

怎么配：

```powershell
notepad $env:USERPROFILE\.config\opencode\tui.jsonc
```

也可用环境变量指定：

```txt
OPENCODE_TUI_CONFIG=自定义路径
```

可用键，常见：

```txt
$schema
theme
keybinds
scroll_speed
scroll_acceleration
diff_style
mouse
```

值类型：

```txt
$schema = "https://opencode.ai/tui.json"
theme = string
keybinds = object
scroll_speed = number
scroll_acceleration = object
diff_style = string，例如 "auto"
mouse = boolean
```

OpenCode 官方现在建议 TUI 相关配置放独立 `tui.json / tui.jsonc`，旧的 `theme`、`keybinds`、`tui` 放在 `opencode.json` 的方式已被标为旧方式并会迁移。([OpenCode][2])

---

# 3. 全局 Rules：`AGENTS.md`

路径：

```txt
%USERPROFILE%\.config\opencode\AGENTS.md
```

怎么配：

```powershell
notepad $env:USERPROFILE\.config\opencode\AGENTS.md
```

文件类型：

```txt
Markdown
```

可用键：

```txt
无固定键值
无 YAML frontmatter
纯 Markdown 指令
```

常见区块：

```txt
Project rules
Coding style
Test commands
Build commands
Forbidden actions
Output format
Review policy
```

兼容 Claude Code fallback：

```txt
%USERPROFILE%\.claude\CLAUDE.md
```

优先级：

```txt
项目 AGENTS.md / CLAUDE.md
> 全局 ~/.config/opencode/AGENTS.md
> 全局 ~/.claude/CLAUDE.md
```

如果同一层同时有 `AGENTS.md` 和 `CLAUDE.md`，OpenCode 优先用 `AGENTS.md`。([OpenCode][3])

---

# 4. 全局自定义 Agent / SubAgent：`agents/*.md`

路径：

```txt
%USERPROFILE%\.config\opencode\agents\<agent-name>.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode\agents -Force
notepad $env:USERPROFILE\.config\opencode\agents\reviewer.md
```

也可以用命令交互式创建：

```powershell
opencode agent create
```

官方说这个命令会询问保存到 global 还是 project、描述、生成 system prompt 和 identifier、选择工具权限，最后创建 markdown agent 文件。([OpenCode][1])

文件类型：

```txt
Markdown + YAML frontmatter
```

frontmatter 可用键：

```yaml
description
mode
model
temperature
top_p
prompt
tools
permission
steps
disable
hidden
color
```

值范围：

```txt
description = string，必填
mode = "primary" | "subagent" | "all"
model = string，格式 provider/model-id
temperature = number，通常 0.0 - 1.0
top_p = number，0.0 - 1.0
prompt = string，可写纯 prompt，也可用 {file:...}
steps = number
disable = boolean
hidden = boolean，仅 subagent 有意义
color = hex color | "primary" | "secondary" | "accent" | "success" | "warning" | "error" | "info"
```

`tools` 可用键，旧方式，官方说已 deprecated，但仍可用：

```yaml
tools:
  bash: boolean
  edit: boolean
  write: boolean
  read: boolean
  grep: boolean
  glob: boolean
  patch: boolean
  todowrite: boolean
  webfetch: boolean
```

更推荐用 `permission`：

```yaml
permission:
  edit: "ask" | "allow" | "deny"
  bash: "ask" | "allow" | "deny" | object
  webfetch: "ask" | "allow" | "deny"
  task: object
  skill: object
```

`permission.bash` / `permission.task` / `permission.skill` 支持 glob：

```txt
"*"
"git *"
"git status *"
"orchestrator-*"
"internal-*"
```

权限值：

```txt
ask
allow
deny
```

OpenCode agent 文件名会成为 agent 名称，例如 `review.md` 创建 `review` agent。它支持 primary agent、subagent、隐藏 subagent、Task 权限、颜色、温度、top_p，以及把额外字段透传给模型 provider。([OpenCode][1])

---

# 5. 在 `opencode.jsonc` 里配置 Agent

路径：

```txt
%USERPROFILE%\.config\opencode\opencode.jsonc
```

配置位置：

```txt
agent.<agent-name>
```

可用键：

```txt
description
mode
model
temperature
top_p
prompt
tools
permission
steps
disable
hidden
color

以及 provider-specific model options
```

额外模型参数示例键，按 provider 透传：

```txt
reasoningEffort
textVerbosity
```

OpenCode 官方写明 agent 可以直接配置在 `opencode.json` 的 `agent` 字段，也可以用 Markdown 文件；额外字段会直接传给 provider 作为模型参数。([OpenCode][1])

---

# 6. 默认 Agent：`default_agent`

路径：

```txt
%USERPROFILE%\.config\opencode\opencode.jsonc
```

配置位置：

```txt
default_agent
```

值类型：

```txt
default_agent = string
```

限制：

```txt
必须是 primary agent
不能是 subagent
```

可填：

```txt
build
plan
自定义 primary agent 名称
```

如果指定不存在或指定了 subagent，OpenCode 会回退到 `build`。([OpenCode][2])

---

# 7. 全局 Commands：`commands/*.md`

路径：

```txt
%USERPROFILE%\.config\opencode\commands\<command-name>.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode\commands -Force
notepad $env:USERPROFILE\.config\opencode\commands\review.md
```

调用方式：

```txt
/review
```

文件类型：

```txt
Markdown + YAML frontmatter
```

frontmatter 可用键：

```yaml
description
agent
model
subtask
```

正文：

```txt
正文内容就是 command template
```

模板变量：

```txt
$ARGUMENTS
$1
$2
$3
...
```

特殊语法：

```txt
!`shell command`
@file/path
```

说明：

```txt
!`...` = 把 shell 输出注入 prompt
@file = 把文件内容注入 prompt
```

如果 command 指定的是 subagent，默认会触发 subagent invocation；要关掉可设 `subtask: false`。([OpenCode][4])

---

# 8. 在 `opencode.jsonc` 里配置 Commands

路径：

```txt
%USERPROFILE%\.config\opencode\opencode.jsonc
```

配置位置：

```txt
command.<command-name>
```

可用键：

```txt
template
description
agent
model
subtask
```

值类型：

```txt
template = string，必填
description = string
agent = string
model = string
subtask = boolean
```

官方说明 command 既可以通过 config 的 `command` 字段配置，也可以通过 `commands/` 目录的 Markdown 文件配置。([OpenCode][4])

---

# 9. 全局 Skills：`skills/<name>/SKILL.md`

OpenCode 支持多套 skill 路径，终于不是每家工具都发明一套孤岛格式，这点人类偶尔还算有救。

OpenCode 原生全局路径：

```txt
%USERPROFILE%\.config\opencode\skills\<skill-name>\SKILL.md
```

Agent Skills 兼容路径：

```txt
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
```

Claude Code 兼容路径：

```txt
%USERPROFILE%\.claude\skills\<skill-name>\SKILL.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode\skills\my-skill -Force
notepad $env:USERPROFILE\.config\opencode\skills\my-skill\SKILL.md
```

文件类型：

```txt
Markdown + YAML frontmatter
```

frontmatter 可用键：

```yaml
name
description
license
compatibility
metadata
```

键值规则：

```txt
name = required
description = required
license = optional
compatibility = optional
metadata = optional，string-to-string map
```

`name` 规则：

```txt
1-64 字符
小写字母/数字/单连字符
不能以 - 开头或结尾
不能包含连续 --
必须匹配所在目录名
regex: ^[a-z0-9]+(-[a-z0-9]+)*$
```

`description`：

```txt
1-1024 字符
```

权限控制位置：

```txt
opencode.jsonc -> permission.skill
agent frontmatter -> permission.skill
agent config -> agent.<name>.permission.skill
```

权限值：

```txt
allow
deny
ask
```

OpenCode skill 是按需加载的：agent 先看到 skill 名称和 description，需要时通过 native `skill` tool 加载完整内容；skill 会从 `.opencode`、`.claude`、`.agents` 和全局目录中发现。([OpenCode][5])

---

# 10. MCP：`mcp` 字段

路径：

```txt
%USERPROFILE%\.config\opencode\opencode.jsonc
```

怎么配：

```powershell
notepad $env:USERPROFILE\.config\opencode\opencode.jsonc
```

也可以用命令：

```powershell
opencode mcp add
opencode mcp list
opencode mcp auth <name>
opencode mcp logout <name>
opencode mcp debug <name>
```

配置位置：

```txt
mcp.<server-name>
```

通用键：

```txt
type
enabled
```

本地 MCP 可用键：

```txt
type = "local"
command = array<string>
enabled = boolean
environment = object<string,string>
```

远程 MCP 可用键：

```txt
type = "remote"
url = string
enabled = boolean
headers = object<string,string>
```

OpenCode MCP 直接写在主配置的 `mcp` 字段里，不像 Windsurf 单独 `mcp_config.json`；本地 MCP 用 `type: "local"` 和 `command`，远程组织默认 MCP 可通过本地 `enabled: true` 覆盖启用。([OpenCode][6])

---

# 11. Provider / Model

路径：

```txt
%USERPROFILE%\.config\opencode\opencode.jsonc
```

凭据路径，`/connect` 或 `opencode auth login` 保存到：

```txt
%USERPROFILE%\.local\share\opencode\auth.json
```

怎么配认证：

```powershell
opencode auth login
opencode auth list
opencode auth logout
```

配置键：

```txt
provider
model
small_model
enabled_providers
disabled_providers
```

`provider.<id>` 可用键：

```txt
models
options
```

`provider.<id>.options` 常见键：

```txt
apiKey
timeout
chunkTimeout
setCacheKey
baseURL
```

Anthropic / OpenAI / Gemini 这类 provider 用：

```txt
provider.<provider-id>.options.apiKey
```

Amazon Bedrock 额外可用：

```txt
region
profile
endpoint
```

变量插值：

```txt
{env:VARIABLE_NAME}
{file:path/to/file}
```

`disabled_providers` 优先级高于 `enabled_providers`，两者冲突时禁用优先。([OpenCode][2])

---

# 12. 全局 Custom Tools：`tools/*.ts / *.js`

路径：

```txt
%USERPROFILE%\.config\opencode\tools\<tool-name>.ts
%USERPROFILE%\.config\opencode\tools\<tool-name>.js
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode\tools -Force
notepad $env:USERPROFILE\.config\opencode\tools\my-tool.ts
```

文件类型：

```txt
TypeScript / JavaScript
```

默认导出工具时，可用字段：

```txt
description
args
execute
```

字段含义：

```txt
description = string
args = object，通常用 tool.schema 或 zod
execute = async function
```

context 可用字段：

```txt
agent
sessionID
messageID
directory
worktree
```

命名规则：

```txt
文件名 = tool 名
多个 named export = <filename>_<exportname>
```

如果自定义工具和内置工具重名，自定义工具优先。别随手建个 `bash.ts`，除非你真想替换内置 bash，不然这就是在给自己埋地雷。([OpenCode][7])

---

# 13. 全局 Plugins：`plugins/*.ts / *.js`

路径：

```txt
%USERPROFILE%\.config\opencode\plugins\<plugin-name>.ts
%USERPROFILE%\.config\opencode\plugins\<plugin-name>.js
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode\plugins -Force
notepad $env:USERPROFILE\.config\opencode\plugins\my-plugin.ts
```

也可以在主配置加载 npm 插件：

```txt
opencode.jsonc -> plugin
```

`plugin` 值类型：

```txt
plugin = array<string>
```

本地插件函数 context：

```txt
project
directory
worktree
client
$
```

插件事件键：

```txt
command.executed

file.edited
file.watcher.updated

installation.updated

lsp.client.diagnostics
lsp.updated

message.part.removed
message.part.updated
message.removed
message.updated

permission.asked
permission.replied

server.connected

session.created
session.compacted
session.deleted
session.diff
session.error
session.idle
session.status
session.updated

todo.updated

shell.env

tool.execute.after
tool.execute.before

tui.prompt.append
tui.command.execute
tui.toast.show
```

插件加载顺序：

```txt
1. 全局 config plugin 字段
2. 项目 config plugin 字段
3. 全局 plugins 目录
4. 项目 plugins 目录
```

npm 插件会自动用 Bun 安装到缓存目录；本地插件如果需要依赖，可以在配置目录放 `package.json`。([OpenCode][8])

---

# 14. 全局 Themes：`themes/*.json`

路径：

```txt
%USERPROFILE%\.config\opencode\themes\<theme-name>.json
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode\themes -Force
notepad $env:USERPROFILE\.config\opencode\themes\my-theme.json
```

配置启用位置：

```txt
%USERPROFILE%\.config\opencode\tui.jsonc
```

主题文件可用键：

```txt
$schema
defs
theme
```

`defs`：

```txt
自定义颜色名 -> 颜色值
```

颜色值支持：

```txt
hex，例如 "#ffffff"
ANSI number，例如 3
颜色引用，例如 "primary"
dark/light object
"none"
```

`theme` 常见键：

```txt
primary
secondary
accent
error
warning
success
info
text
textMuted
background
backgroundPanel
backgroundElement
border
borderActive
borderSubtle
```

OpenCode 主题从 built-in、用户目录、项目目录、当前工作目录加载，后面的优先。([OpenCode][9])

---

# 15. 旧 Modes：`modes/*.md`，不建议新建

路径：

```txt
%USERPROFILE%\.config\opencode\modes\<mode-name>.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.config\opencode\modes -Force
notepad $env:USERPROFILE\.config\opencode\modes\review.md
```

状态：

```txt
deprecated
现在推荐用 agent 字段替代
```

frontmatter 可用键：

```yaml
model
temperature
prompt
tools
```

`tools` 可用：

```txt
bash
edit
write
read
grep
glob
patch
todowrite
webfetch
```

官方已经明确提示：Modes 现在通过 `agent` 配置，`mode` 选项已 deprecated。所以新体系别再围着 modes 打转，除非你在迁移旧配置。([OpenCode][10])

---

# 16. Managed / 企业强制配置

Windows 系统级路径：

```txt
%ProgramData%\opencode\opencode.json
%ProgramData%\opencode\opencode.jsonc
```

怎么配：

```powershell
notepad $env:ProgramData\opencode\opencode.jsonc
```

特点：

```txt
管理员权限
用户不可覆盖
最高优先级之一
```

macOS：

```txt
/Library/Application Support/opencode/opencode.json
/Library/Application Support/opencode/opencode.jsonc
```

Linux：

```txt
/etc/opencode/opencode.json
/etc/opencode/opencode.jsonc
```

macOS MDM managed preferences：

```txt
/Library/Managed Preferences/<user>/ai.opencode.managed.plist
/Library/Managed Preferences/ai.opencode.managed.plist
```

managed config 里的 key 直接映射 `opencode.json` 字段。([OpenCode][2])

---

# 17. 环境变量配置入口

可用环境变量：

```txt
OPENCODE_CONFIG
OPENCODE_TUI_CONFIG
OPENCODE_CONFIG_DIR
OPENCODE_CONFIG_CONTENT
OPENCODE_DISABLE_AUTOUPDATE
OPENCODE_AUTO_SHARE
OPENCODE_GIT_BASH_PATH
OPENCODE_DISABLE_CLAUDE_CODE
OPENCODE_DISABLE_CLAUDE_CODE_PROMPT
OPENCODE_DISABLE_CLAUDE_CODE_SKILLS
```

作用：

```txt
OPENCODE_CONFIG = 指定单个 config 文件路径
OPENCODE_TUI_CONFIG = 指定 TUI 配置文件路径
OPENCODE_CONFIG_DIR = 指定配置目录，里面可放 agents/commands/modes/plugins 等
OPENCODE_CONFIG_CONTENT = 直接传 inline JSON 配置
```

`OPENCODE_CONFIG_DIR` 会像标准 `.opencode` 目录一样搜索 agents、commands、modes、plugins，并且加载在 global config 和 `.opencode` 目录之后，可覆盖它们。([OpenCode][2])

---

# 18. 项目级对应路径

项目级主配置：

```txt
<project>\opencode.json
<project>\opencode.jsonc
```

项目级 TUI：

```txt
<project>\tui.json
<project>\tui.jsonc
```

项目级 Rules：

```txt
<project>\AGENTS.md
<project>\CLAUDE.md
```

项目级 Agents：

```txt
<project>\.opencode\agents\<agent-name>.md
```

项目级 Commands：

```txt
<project>\.opencode\commands\<command-name>.md
```

项目级 Skills：

```txt
<project>\.opencode\skills\<skill-name>\SKILL.md
<project>\.agents\skills\<skill-name>\SKILL.md
<project>\.claude\skills\<skill-name>\SKILL.md
```

项目级 Tools：

```txt
<project>\.opencode\tools\<tool-name>.ts
<project>\.opencode\tools\<tool-name>.js
```

项目级 Plugins：

```txt
<project>\.opencode\plugins\<plugin-name>.ts
<project>\.opencode\plugins\<plugin-name>.js
```

项目级 Themes：

```txt
<project>\.opencode\themes\<theme-name>.json
```

项目级 Modes，旧：

```txt
<project>\.opencode\modes\<mode-name>.md
```

OpenCode 会从当前目录向上查找项目配置，项目配置会覆盖 global；`.opencode` 和 `~/.config/opencode` 下的子目录使用复数名：`agents/`、`commands/`、`modes/`、`plugins/`、`skills/`、`tools/`、`themes/`，单数旧名也兼容。([OpenCode][2])

---

# 19. 最终速查表

```txt
# 全局主配置
%USERPROFILE%\.config\opencode\opencode.jsonc
键：server / tools / provider / model / small_model / agent / default_agent / share / command / snapshot / autoupdate / formatter / permission / compaction / watcher / mcp / plugin / instructions / disabled_providers / enabled_providers / experimental

# 全局 TUI 配置
%USERPROFILE%\.config\opencode\tui.jsonc
键：theme / keybinds / scroll_speed / scroll_acceleration / diff_style / mouse

# 全局规则
%USERPROFILE%\.config\opencode\AGENTS.md
键：无，纯 Markdown

# 全局 Claude fallback
%USERPROFILE%\.claude\CLAUDE.md
键：无，纯 Markdown

# 全局 Agent / SubAgent
%USERPROFILE%\.config\opencode\agents\<name>.md
键：description / mode / model / temperature / top_p / prompt / tools / permission / steps / disable / hidden / color

# 全局命令
%USERPROFILE%\.config\opencode\commands\<name>.md
键：description / agent / model / subtask

# 全局 Skill
%USERPROFILE%\.config\opencode\skills\<name>\SKILL.md
键：name / description / license / compatibility / metadata

# Agent Skills 兼容路径
%USERPROFILE%\.agents\skills\<name>\SKILL.md
键：name / description / license / compatibility / metadata

# Claude Skills 兼容路径
%USERPROFILE%\.claude\skills\<name>\SKILL.md
键：name / description / license / compatibility / metadata

# 全局 MCP
%USERPROFILE%\.config\opencode\opencode.jsonc -> mcp
键：type / command / environment / url / enabled / headers

# 全局自定义工具
%USERPROFILE%\.config\opencode\tools\<name>.ts
键：description / args / execute

# 全局插件
%USERPROFILE%\.config\opencode\plugins\<name>.ts
键：导出 plugin function，返回事件 hooks

# 全局主题
%USERPROFILE%\.config\opencode\themes\<name>.json
键：$schema / defs / theme

# 旧模式，不建议新建
%USERPROFILE%\.config\opencode\modes\<name>.md
键：model / temperature / prompt / tools

# 凭据
%USERPROFILE%\.local\share\opencode\auth.json
由 opencode auth login / /connect 管理，不建议手改
```

一句话总结：**OpenCode 的关键路径是 `~/.config/opencode/`，Agent 在 `agents/`，Skill 在 `skills/`，Command 在 `commands/`，MCP 写进 `opencode.jsonc`，规则用 `AGENTS.md`