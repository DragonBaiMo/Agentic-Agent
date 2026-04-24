## 0. 全局目录总览

```txt
%USERPROFILE%\.codex\
```

等价于：

```txt
C:\Users\你的用户名\.codex\
```

可配置文件/目录：

```txt
%USERPROFILE%\.codex\config.toml
%USERPROFILE%\.codex\AGENTS.md
%USERPROFILE%\.codex\AGENTS.override.md
%USERPROFILE%\.codex\agents\*.toml
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
%USERPROFILE%\.agents\skills\<skill-name>\agents\openai.yaml
%USERPROFILE%\.codex\hooks.json
```

创建目录：

```powershell
mkdir $env:USERPROFILE\.codex -Force
mkdir $env:USERPROFILE\.codex\agents -Force
mkdir $env:USERPROFILE\.agents\skills -Force
```

打开主配置：

```powershell
notepad $env:USERPROFILE\.codex\config.toml
```

在 IDE Extension 里也可以从右上角齿轮打开：`Codex Settings > Open config.toml`。([OpenAI开发者][1])

---

# 1. `%USERPROFILE%\.codex\config.toml`

这是**全局主配置文件**。模型、审批、沙箱、MCP、SubAgent 并发、Skills 开关、Provider、Web Search、Windows sandbox 等都放这里。人类终于把所有开关塞进一个文件了，像把整栋楼的电闸装在床头柜里。

官方配置优先级是：CLI 参数最高，其次 profile、项目 `.codex/config.toml`、用户 `~/.codex/config.toml`、系统 `/etc/codex/config.toml`、内置默认值。([OpenAI开发者][1])

## 1.1 顶层常用键

```toml
model
model_provider
model_reasoning_effort
model_reasoning_summary
model_supports_reasoning_summaries
model_verbosity
model_context_window
model_auto_compact_token_limit
model_catalog_json
model_instructions_file

approval_policy
approvals_reviewer
sandbox_mode
service_tier
profile
personality
plan_mode_reasoning_effort
review_model

web_search
tools.web_search
tools.view_image
file_opener

developer_instructions
compact_prompt
experimental_compact_prompt_file
instructions

openai_base_url
chatgpt_base_url
forced_login_method
forced_chatgpt_workspace_id
cli_auth_credentials_store

allow_login_shell
default_permissions
project_doc_fallback_filenames
project_doc_max_bytes
project_root_markers

notify
log_dir
sqlite_home
tool_output_token_limit

hide_agent_reasoning
show_raw_agent_reasoning
commit_attribution
check_for_update_on_startup
disable_paste_burst
suppress_unstable_features_warning
feedback.enabled
analytics.enabled
```

其中关键值范围：

```txt
approval_policy = untrusted | on-request | never | granular object
sandbox_mode = read-only | workspace-write | danger-full-access
model_reasoning_effort = minimal | low | medium | high | xhigh
model_reasoning_summary = auto | concise | detailed | none
model_verbosity = low | medium | high
service_tier = flex | fast
personality = none | friendly | pragmatic
web_search = disabled | cached | live
file_opener = vscode | vscode-insiders | windsurf | cursor | none
forced_login_method = chatgpt | api
cli_auth_credentials_store = file | keyring | auto
```

这些键来自官方 Config Reference，包括模型、审批、沙箱、模型 provider、web search、Windows sandbox 等配置项。([OpenAI开发者][2]) ([OpenAI开发者][2]) ([OpenAI开发者][2])

## 1.2 `[agents]` / `agents.*`

用于全局 SubAgent / multi-agent 控制。

```toml
[agents]
max_threads
max_depth
job_max_runtime_seconds
```

也可以定义角色映射：

```toml
[agents.<name>]
description
config_file
nickname_candidates
```

值类型：

```txt
agents.max_threads = number
agents.max_depth = number
agents.job_max_runtime_seconds = number
agents.<name>.description = string
agents.<name>.config_file = string path
agents.<name>.nickname_candidates = array<string>
```

官方说明 `agents.max_threads` 默认 6，`agents.max_depth` 默认 1；自定义 agent 也可以通过独立 TOML 文件放在 `~/.codex/agents/`。([OpenAI开发者][3])

## 1.3 `[features]`

功能开关。

```toml
[features]
apps
codex_hooks
enable_request_compression
fast_mode
memories
multi_agent
personality
prevent_idle_sleep
shell_snapshot
shell_tool
skill_mcp_dependency_install
undo
unified_exec
web_search
web_search_cached
web_search_request
```

值类型基本都是：

```txt
boolean
```

注意：`features.web_search*` 是旧开关，官方建议优先用顶层 `web_search`。`features.multi_agent` 控制 `spawn_agent`、`send_input`、`resume_agent`、`wait_agent`、`close_agent` 等多代理工具。([OpenAI开发者][2])

## 1.4 `[mcp_servers.<id>]`

MCP 不单独放一个文件，直接写进 `config.toml`。官方说 MCP 配置默认在 `~/.codex/config.toml`，CLI 和 IDE Extension 共用。([OpenAI开发者][4])

STDIO MCP 可用键：

```toml
[mcp_servers.<id>]
command
args
env
env_vars
cwd
experimental_environment
startup_timeout_sec
startup_timeout_ms
tool_timeout_sec
enabled
required
enabled_tools
disabled_tools
```

HTTP MCP 可用键：

```toml
[mcp_servers.<id>]
url
bearer_token_env_var
http_headers
env_http_headers
oauth_resource
scopes
startup_timeout_sec
startup_timeout_ms
tool_timeout_sec
enabled
required
enabled_tools
disabled_tools
```

MCP OAuth 顶层键：

```toml
mcp_oauth_callback_port
mcp_oauth_callback_url
mcp_oauth_credentials_store
```

值类型大致是：

```txt
command = string
args = array<string>
env = map<string,string>
env_vars = array<string | { name = string, source = "local" | "remote" }>
cwd = string
experimental_environment = local | remote
url = string
bearer_token_env_var = string
http_headers = map<string,string>
env_http_headers = map<string,string>
enabled = boolean
required = boolean
enabled_tools = array<string>
disabled_tools = array<string>
startup_timeout_sec = number
tool_timeout_sec = number
scopes = array<string>
```

官方 MCP 文档列出了 STDIO、HTTP、OAuth、超时、工具 allow/deny list 等字段。([OpenAI开发者][4])

## 1.5 `[[skills.config]]`

用于全局启用/禁用 Skill。

```toml
[[skills.config]]
path
enabled
```

键值：

```txt
path = string path
enabled = boolean
```

官方文档说可以用 `[[skills.config]]` 在 `~/.codex/config.toml` 里禁用某个 skill，改完需要重启 Codex。([OpenAI开发者][5])

## 1.6 `[model_providers.<id>]`

自定义模型 provider。

```toml
[model_providers.<id>]
name
base_url
env_key
env_key_instructions
experimental_bearer_token
http_headers
env_http_headers
query_params
request_max_retries
stream_max_retries
stream_idle_timeout_ms
requires_openai_auth
supports_websockets
wire_api
```

命令式 token：

```toml
[model_providers.<id>.auth]
command
args
cwd
refresh_interval_ms
timeout_ms
```

值类型：

```txt
name = string
base_url = string
env_key = string
env_key_instructions = string
experimental_bearer_token = string
http_headers = map<string,string>
env_http_headers = map<string,string>
query_params = map<string,string>
request_max_retries = number
stream_max_retries = number
stream_idle_timeout_ms = number
requires_openai_auth = boolean
supports_websockets = boolean
wire_api = responses
auth.command = string
auth.args = array<string>
auth.cwd = string path
auth.refresh_interval_ms = number
auth.timeout_ms = number
```

官方说明内置 provider id 如 `openai`、`ollama`、`lmstudio` 不能覆盖。([OpenAI开发者][2])

## 1.7 `[profiles.<name>]`

Profile 可以覆盖多数配置键。

常见：

```toml
[profiles.<name>]
model
model_provider
model_reasoning_effort
model_instructions_file
model_catalog_json
approval_policy
sandbox_mode
service_tier
web_search
personality
plan_mode_reasoning_effort
oss_provider
tools_view_image
```

还可以：

```toml
[profiles.<name>.analytics]
enabled

[profiles.<name>.windows]
sandbox
```

官方说 `profiles.<name>.*` 是对支持配置键的 profile-scoped overrides。([OpenAI开发者][2])

## 1.8 `[permissions.<name>]`

权限 profile。

```toml
[permissions.<name>.filesystem]
:path-or-glob
":project_roots".<subpath-or-glob>
glob_scan_max_depth

[permissions.<name>.network]
enabled
mode
domains
proxy_url
socks_url
allow_local_binding
allow_upstream_proxy
enable_socks5
enable_socks5_udp
unix_sockets
dangerously_allow_all_unix_sockets
dangerously_allow_non_loopback_proxy
```

值范围：

```txt
filesystem path value = read | write | none | table
network.mode = limited | full
network.domains = map<string, allow | deny>
network.unix_sockets = map<string, allow | none>
```

官方权限字段包括 filesystem、network、domain rules、proxy、SOCKS5、Unix socket 等。([OpenAI开发者][2]) ([OpenAI开发者][2])

## 1.9 `[sandbox_workspace_write]`

```toml
[sandbox_workspace_write]
writable_roots
network_access
exclude_slash_tmp
exclude_tmpdir_env_var
```

值类型：

```txt
writable_roots = array<string>
network_access = boolean
exclude_slash_tmp = boolean
exclude_tmpdir_env_var = boolean
```

## 1.10 `[shell_environment_policy]`

```toml
[shell_environment_policy]
inherit
include_only
exclude
set
ignore_default_excludes
experimental_use_profile
```

值类型：

```txt
inherit = all | core | none
include_only = array<string>
exclude = array<string>
set = map<string,string>
ignore_default_excludes = boolean
experimental_use_profile = boolean
```

## 1.11 `[windows]`

Windows 原生 sandbox。

```toml
[windows]
sandbox
sandbox_private_desktop
```

值类型：

```txt
sandbox = unelevated | elevated
sandbox_private_desktop = boolean
```

官方建议 Windows 原生运行时用 `elevated`，失败或无管理员权限再用 `unelevated`。([OpenAI开发者][1])

## 1.12 `[memories]`

```toml
[memories]
consolidation_model
extract_model
disable_on_external_context
generate_memories
max_raw_memories_for_consolidation
max_rollout_age_days
max_rollouts_per_startup
max_unused_days
min_rollout_idle_hours
use_memories
```

值类型：

```txt
*_model = string
disable_on_external_context = boolean
generate_memories = boolean
use_memories = boolean
max_* = number
min_rollout_idle_hours = number
```

## 1.13 `[tui]`

```toml
[tui]
alternate_screen
animations
notification_condition
notification_method
notifications
show_tooltips
status_line
terminal_title
theme
model_availability_nux.<model>
```

值类型：

```txt
alternate_screen = auto | always | never
animations = boolean
notification_condition = unfocused | always
notification_method = auto | osc9 | bel
notifications = boolean | array<string>
show_tooltips = boolean
status_line = array<string> | null
terminal_title = array<string> | null
theme = string
```

## 1.14 `[otel]`

```toml
[otel]
environment
exporter
metrics_exporter
trace_exporter
log_user_prompt
```

Exporter 相关：

```toml
[otel.exporter.<id>]
endpoint
headers
protocol

[otel.exporter.<id>.tls]
ca-certificate
client-certificate
client-private-key

[otel.trace_exporter.<id>]
endpoint
headers
protocol

[otel.trace_exporter.<id>.tls]
ca-certificate
client-certificate
client-private-key
```

值范围：

```txt
exporter = none | otlp-http | otlp-grpc
metrics_exporter = none | statsig | otlp-http | otlp-grpc
trace_exporter = none | otlp-http | otlp-grpc
protocol = binary | json
```

---

# 2. `%USERPROFILE%\.codex\AGENTS.md`

全局长期指令文件。所有仓库都会继承它。官方说全局范围内 Codex 会先读 `AGENTS.override.md`，如果没有才读 `AGENTS.md`，且这一层只取第一个非空文件。([OpenAI开发者][6])

这个文件不是 TOML，不是 JSON，就是 Markdown。没有固定“键值”，但通常可以写这些 Markdown 区块：

```md
# 标题

## Working agreements
## Coding rules
## Testing rules
## Commit rules
## Security rules
## Output format
## Forbidden actions
## Project preferences
```

可配置方式：

```powershell
notepad $env:USERPROFILE\.codex\AGENTS.md
```

---

# 3. `%USERPROFILE%\.codex\AGENTS.override.md`

全局临时覆盖指令。存在时优先于 `AGENTS.md`。适合临时改变 Codex 行为，比如“今天只做审查不改代码”。官方明确说可以用它做 temporary global override，删掉后恢复基础 guidance。([OpenAI开发者][6])

文件类型：

```txt
Markdown
```

可写内容：

```md
# 临时覆盖说明

## Temporary rules
## Current task mode
## Restrictions
## Output format
```

打开方式：

```powershell
notepad $env:USERPROFILE\.codex\AGENTS.override.md
```

---

# 4. `%USERPROFILE%\.codex\agents\*.toml`

全局自定义 Agent / SubAgent 文件。每个 `.toml` 文件定义一个 custom agent。官方要求每个 custom agent 文件必须包含 `name`、`description`、`developer_instructions`。其他字段可以继承父 session，也可以覆盖普通 `config.toml` 里的键，比如 `model`、`model_reasoning_effort`、`sandbox_mode`、`mcp_servers`、`skills.config`。([OpenAI开发者][3])

路径：

```txt
%USERPROFILE%\.codex\agents\<agent-name>.toml
```

创建/打开：

```powershell
notepad $env:USERPROFILE\.codex\agents\reviewer.toml
```

必填键：

```toml
name
description
developer_instructions
```

可选专属键：

```toml
nickname_candidates
```

也可写入大部分 `config.toml` 支持键，常见：

```toml
model
model_provider
model_reasoning_effort
model_reasoning_summary
model_verbosity
sandbox_mode
approval_policy
developer_instructions

[mcp_servers.<id>]
command
args
env
env_vars
cwd
url
bearer_token_env_var
http_headers
env_http_headers
startup_timeout_sec
tool_timeout_sec
enabled
required
enabled_tools
disabled_tools

[[skills.config]]
path
enabled
```

值类型：

```txt
name = string
description = string
developer_instructions = string
nickname_candidates = array<string>
model = string
model_reasoning_effort = minimal | low | medium | high | xhigh
sandbox_mode = read-only | workspace-write | danger-full-access
```

官方说 `name` 字段才是 custom agent 的真实标识，文件名只是推荐保持一致。([OpenAI开发者][7])

---

# 5. `%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md`

全局 Skill 文件。注意：**Skill 不在 `.codex` 目录里，而是在 `%USERPROFILE%\.agents\skills`**。官方写明用户级 Skill 路径是 `$HOME/.agents/skills`；每个 skill 是一个目录，里面必须有 `SKILL.md`，可选 `scripts/`、`references/`、`assets/`、`agents/openai.yaml`。([OpenAI开发者][5])

路径：

```txt
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
```

可选目录：

```txt
%USERPROFILE%\.agents\skills\<skill-name>\scripts\
%USERPROFILE%\.agents\skills\<skill-name>\references\
%USERPROFILE%\.agents\skills\<skill-name>\assets\
%USERPROFILE%\.agents\skills\<skill-name>\agents\openai.yaml
```

创建：

```powershell
mkdir $env:USERPROFILE\.agents\skills\my-skill -Force
notepad $env:USERPROFILE\.agents\skills\my-skill\SKILL.md
```

`SKILL.md` 是 Markdown + YAML frontmatter。

必填 frontmatter：

```yaml
name
description
```

正文无固定键值，是给 Codex 的技能说明。常见 Markdown 区块：

```md
# Skill title

## Purpose
## When to use
## Inputs
## Steps
## Output format
## Constraints
## Examples
```

官方说 Codex 先只看 skill metadata，包括 `name`、`description`、路径和可选 `agents/openai.yaml`，真正决定使用时才加载完整 `SKILL.md`。([OpenAI开发者][5])

---

# 6. `%USERPROFILE%\.agents\skills\<skill-name>\agents\openai.yaml`

Skill 的可选 UI / 策略 / 依赖元数据。不是必须，但适合做更工程化的 Skill 包。官方说 `agents/openai.yaml` 可用于配置 UI metadata、调用策略、工具依赖。([OpenAI开发者][5])

路径：

```txt
%USERPROFILE%\.agents\skills\<skill-name>\agents\openai.yaml
```

创建：

```powershell
mkdir $env:USERPROFILE\.agents\skills\my-skill\agents -Force
notepad $env:USERPROFILE\.agents\skills\my-skill\agents\openai.yaml
```

可用键：

```yaml
interface:
  display_name
  short_description
  icon_small
  icon_large
  brand_color
  default_prompt

policy:
  allow_implicit_invocation

dependencies:
  tools:
    - type
      value
      description
      transport
      url
```

值类型：

```txt
interface.display_name = string
interface.short_description = string
interface.icon_small = string path
interface.icon_large = string path
interface.brand_color = string hex color
interface.default_prompt = string

policy.allow_implicit_invocation = boolean

dependencies.tools[].type = string，例如 mcp
dependencies.tools[].value = string
dependencies.tools[].description = string
dependencies.tools[].transport = string，例如 streamable_http
dependencies.tools[].url = string
```

---

# 7. `%USERPROFILE%\.codex\hooks.json`

全局 Hooks 文件。先说坑：官方写明 Hooks 仍是 experimental，而且 **Windows support temporarily disabled**。所以你 Windows 上配了也可能暂时不生效，人类工程史的一贯传统：文档里有，现实里暂缓。([OpenAI开发者][8])

路径：

```txt
%USERPROFILE%\.codex\hooks.json
```

启用位置：

```txt
%USERPROFILE%\.codex\config.toml
```

需要在 `config.toml` 里启用：

```toml
[features]
codex_hooks = true
```

打开：

```powershell
notepad $env:USERPROFILE\.codex\hooks.json
```

顶层 JSON 键：

```json
hooks
```

事件键：

```json
SessionStart
PreToolUse
PermissionRequest
PostToolUse
UserPromptSubmit
Stop
```

每个事件下的 matcher group 可用键：

```json
matcher
hooks
```

每个 hook handler 可用键：

```json
type
command
statusMessage
timeout
timeoutSec
```

值类型：

```txt
matcher = string regex，可省略
hooks = array<object>
type = command
command = string
statusMessage = string，可选
timeout = number，秒
timeoutSec = number，timeout 的别名
```

官方说明 hook 结构是三层：事件名、matcher group、handler；`timeout` 单位是秒，默认 600；`statusMessage` 可选。([OpenAI开发者][8])

各事件 matcher 行为：

```txt
SessionStart.matcher -> 匹配 startup | resume
PreToolUse.matcher -> 匹配 tool name，目前主要是 Bash
PermissionRequest.matcher -> 匹配 tool name，目前主要是 Bash
PostToolUse.matcher -> 匹配 tool name，目前主要是 Bash
UserPromptSubmit.matcher -> 当前忽略
Stop.matcher -> 当前忽略
```

官方也提醒目前 `PreToolUse`、`PostToolUse` 主要只拦 Bash，不拦 MCP、Write、WebSearch 等非 shell 工具。([OpenAI开发者][8])

---

# 8. 最小“全局可配置路径”清单

你真正日常会碰的就这些：

```txt
# Codex 主配置
%USERPROFILE%\.codex\config.toml

# 全局长期指令
%USERPROFILE%\.codex\AGENTS.md

# 全局临时覆盖指令
%USERPROFILE%\.codex\AGENTS.override.md

# 全局自定义 Agent / SubAgent
%USERPROFILE%\.codex\agents\*.toml

# 全局 Skills
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md

# Skill 可选元数据
%USERPROFILE%\.agents\skills\<skill-name>\agents\openai.yaml

# 全局 Hooks，实验性，Windows 暂不可用/受限
%USERPROFILE%\.codex\hooks.json
```

最重要的对应关系：

```txt
config.toml
= 模型、MCP、审批、沙箱、SubAgent 并发、Provider、Skills 开关

AGENTS.md
= 全局长期提示词/规则

AGENTS.override.md
= 全局临时覆盖提示词/规则

agents/*.toml
= 真正的自定义 Agent / SubAgent 定义

.agents/skills/*/SKILL.md
= 全局 Skill 能力包

.agents/skills/*/agents/openai.yaml
= Skill UI、调用策略、依赖声明

hooks.json
= 生命周期脚本钩子
```

路径别再乱放。Codex 这套最容易搞错的就是：**Agent 在 `.codex/agents`，Skill 在 `.agents/skills`，MCP 在 `.codex/config.toml`，全局提示词在 `.codex/AGENTS.md`**。这四个一错，后面全是电子玄学。
