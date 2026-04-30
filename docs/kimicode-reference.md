# 0. 总路径速览，Windows

```txt
# Kimi Code 主运行目录
%USERPROFILE%\.kimi\

# 主配置
%USERPROFILE%\.kimi\config.toml
%USERPROFILE%\.kimi\config.json   # 旧配置会自动迁移到 config.toml

# MCP 配置
%USERPROFILE%\.kimi\mcp.json

# OAuth / 登录凭据
%USERPROFILE%\.kimi\credentials\<provider>.json

# 会话数据
%USERPROFILE%\.kimi\sessions\<work-dir-hash>\<session-id>\

# Plan mode 文件
%USERPROFILE%\.kimi\plans\<slug>.md

# 用户输入历史
%USERPROFILE%\.kimi\user-history\<work-dir-hash>.jsonl

# 日志
%USERPROFILE%\.kimi\logs\kimi.log

# 用户级 Skills，Kimi 专属优先
%USERPROFILE%\.kimi\skills\<skill-name>\SKILL.md

# 用户级 Skills，通用推荐
%USERPROFILE%\.config\agents\skills\<skill-name>\SKILL.md

# 用户级 Skills，兼容路径
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
%USERPROFILE%\.claude\skills\<skill-name>\SKILL.md
%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md
```

Kimi Code 默认把配置、会话、日志、MCP、凭据都放在 `~/.kimi/`；可以用 `KIMI_SHARE_DIR` 改运行数据目录，但**它不影响 Skills 搜索路径**，这个坑很典型，像把遥控器和电池分别藏在两个抽屉里。([Moonshot AI][2])

---

# 1. 主配置：`%USERPROFILE%\.kimi\config.toml`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.kimi -Force
notepad $env:USERPROFILE\.kimi\config.toml
```

也可以启动时指定：

```powershell
kimi --config-file C:\path\to\config.toml
kimi --config '{"default_model": "kimi-for-coding"}'
```

官方说明默认配置文件是 `~/.kimi/config.toml`，首次运行不存在时会自动创建；同时支持 TOML 和 JSON，旧 `config.json` 会自动迁移并备份成 `config.json.bak`。([Moonshot AI][3])

## 顶层可用键

```txt
default_model
default_thinking
default_yolo
default_plan_mode
default_editor
theme
show_thinking_stream
merge_all_available_skills
extra_skill_dirs

providers
models
loop_control
background
services
mcp
hooks
```

值类型：

```txt
default_model = string
default_thinking = boolean
default_yolo = boolean
default_plan_mode = boolean
default_editor = string
theme = "dark" | "light"
show_thinking_stream = boolean
merge_all_available_skills = boolean
extra_skill_dirs = array<string>
```

这些是官方配置页列出的主配置项；其中 `merge_all_available_skills` 控制是否合并 Kimi / Claude / Codex 等多品牌 Skills 目录。([Moonshot AI][3])

---

# 2. Provider：`[providers.<name>]`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置位置：

```toml
[providers.<provider-name>]
```

可用键：

```txt
type
base_url
api_key
env
custom_headers
```

值类型：

```txt
type = "kimi" | "openai_legacy" | "openai_responses" | "anthropic" | "gemini" | "vertexai"
base_url = string
api_key = string
env = table
custom_headers = table
```

Kimi Code 支持多种 provider 类型，包括 Kimi API、OpenAI Chat Completions、OpenAI Responses、Anthropic、Gemini、Vertex AI；`custom_headers` 可用于所有 provider。([Moonshot AI][4])

---

# 3. Model：`[models.<name>]`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置位置：

```toml
[models.<model-name>]
```

可用键：

```txt
provider
model
max_context_size
capabilities
display_name
```

值类型：

```txt
provider = string
model = string
max_context_size = integer
capabilities = array<string>
display_name = string
```

`capabilities` 可用值：

```txt
thinking
always_thinking
image_in
video_in
```

`thinking` 表示支持思考模式；`always_thinking` 表示模型总是思考，不能关闭；`image_in` / `video_in` 控制图片和视频输入能力。([Moonshot AI][4])

---

# 4. Loop Control：`[loop_control]`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置位置：

```toml
[loop_control]
```

可用键：

```txt
max_steps_per_turn
max_steps_per_run
max_retries_per_step
max_ralph_iterations
reserved_context_size
compaction_trigger_ratio
```

值类型：

```txt
max_steps_per_turn = integer
max_steps_per_run = integer
max_retries_per_step = integer
max_ralph_iterations = integer
reserved_context_size = integer
compaction_trigger_ratio = float
```

`max_steps_per_turn` 控制每轮 Agent 最大步骤数；`reserved_context_size` 和 `compaction_trigger_ratio` 控制自动压缩触发。官方配置页把这一组归为 agent execution loop。([Moonshot AI][3])

---

# 5. Background：`[background]`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置位置：

```toml
[background]
```

可用键：

```txt
max_running_tasks
keep_alive_on_exit
kill_grace_period_ms
agent_task_timeout_s
print_wait_ceiling_s
```

值类型：

```txt
max_running_tasks = integer
keep_alive_on_exit = boolean
kill_grace_period_ms = integer
agent_task_timeout_s = integer
print_wait_ceiling_s = integer
```

这些控制后台任务运行，例如 Shell 工具和 Agent 工具以 `run_in_background=true` 启动时的并发数、超时和退出行为。([Moonshot AI][3])

---

# 6. Services：`[services.moonshot_search]` / `[services.moonshot_fetch]`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置位置：

```toml
[services.moonshot_search]
[services.moonshot_fetch]
```

可用键：

```txt
base_url
api_key
custom_headers
```

值类型：

```txt
base_url = string
api_key = string
custom_headers = table
```

`moonshot_search` 对应 `SearchWeb` 工具；`moonshot_fetch` 对应 `FetchURL` 工具。官方说明通过 `/login` 选择 Kimi Code platform 时会自动配置 search 和 fetch；其他平台下 `SearchWeb` 可能不可用，`FetchURL` 会退回本地抓取。([Moonshot AI][3])

---

# 7. MCP 总配置：`%USERPROFILE%\.kimi\mcp.json`

路径：

```txt
%USERPROFILE%\.kimi\mcp.json
```

怎么配：

```powershell
notepad $env:USERPROFILE\.kimi\mcp.json
```

也可以用命令管理：

```powershell
kimi mcp add --transport http context7 https://mcp.context7.com/mcp
kimi mcp add --transport stdio chrome-devtools -- npx chrome-devtools-mcp@latest
kimi mcp list
kimi mcp remove context7
kimi mcp auth linear
kimi mcp test context7
```

顶层键：

```json
mcpServers
```

HTTP MCP 可用键：

```txt
url
transport
headers
```

STDIO MCP 可用键：

```txt
command
args
env
```

常见字段：

```txt
mcpServers.<id>.url = string
mcpServers.<id>.transport = "http" | "stdio"
mcpServers.<id>.headers = object
mcpServers.<id>.command = string
mcpServers.<id>.args = array<string>
mcpServers.<id>.env = object
```

Kimi Code 的 MCP 文件是 `~/.kimi/mcp.json`，格式兼容常见 MCP client；也可以启动时用 `--mcp-config-file` 或 `--mcp-config` 临时加载。([Moonshot AI][5])

---

# 8. MCP client 行为：`[mcp.client]`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置位置：

```toml
[mcp.client]
```

可用键：

```txt
tool_call_timeout_ms
```

值类型：

```txt
tool_call_timeout_ms = integer
```

这个只控制 MCP client 行为，比如工具调用超时；真正 MCP server 列表在 `~/.kimi/mcp.json`。([Moonshot AI][3])

---

# 9. Hooks：`[[hooks]]`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置位置：

```toml
[[hooks]]
```

可用键：

```txt
event
command
matcher
timeout
```

值类型：

```txt
event = string
command = string
matcher = string
timeout = integer
```

支持事件：

```txt
PreToolUse
PostToolUse
PostToolUseFailure
UserPromptSubmit
Stop
StopFailure
SessionStart
SessionEnd
SubagentStart
SubagentStop
PreCompact
PostCompact
Notification
```

事件 matcher 规则：

```txt
PreToolUse / PostToolUse / PostToolUseFailure -> matcher 匹配 tool name
SessionStart -> matcher 匹配 startup / resume
SessionEnd -> matcher 匹配 reason
SubagentStart / SubagentStop -> matcher 匹配 agent name
PreCompact / PostCompact -> matcher 匹配 trigger
Notification -> matcher 匹配 sink
```

Hook 命令会通过 stdin 收到 JSON 上下文；退出码 `0` 允许，退出码 `2` 阻断并把 stderr 反馈给模型，其他退出码默认放行。也可以输出结构化 JSON，通过 `permissionDecision = "deny"` 阻断操作。注意 Hooks 仍是 Beta。([Moonshot AI][6])

---

# 10. 自定义 Agent 文件：任意路径 `.yaml`

官方加载方式：

```powershell
kimi --agent-file C:\path\to\my-agent.yaml
```

也可以选择内置 agent：

```powershell
kimi --agent default
kimi --agent okabe
```

文件类型：

```txt
YAML
```

基础结构：

```yaml
version
agent
```

`agent` 可用键：

```yaml
extend
name
system_prompt_path
system_prompt_args
tools
exclude_tools
subagents
```

值类型：

```txt
version = integer
agent.extend = "default" | relative path
agent.name = string
agent.system_prompt_path = string path
agent.system_prompt_args = object
agent.tools = array<string>
agent.exclude_tools = array<string>
agent.subagents = object
```

工具字符串格式：

```txt
module:ClassName
```

例如：

```txt
kimi_cli.tools.shell:Shell
kimi_cli.tools.file:ReadFile
kimi_cli.tools.file:WriteFile
```

官方明确：Agent 文件用 YAML 定义，通过 `--agent-file` 加载；可以 `extend: default` 继承内置 agent，也可以继承另一个相对路径 agent 文件。([Moonshot AI][1])

---

# 11. System Prompt 文件：任意路径 `.md`

由 Agent YAML 引用：

```yaml
system_prompt_path: ./system.md
```

文件类型：

```txt
Markdown 模板
```

内置变量：

```txt
${KIMI_NOW}
${KIMI_WORK_DIR}
${KIMI_WORK_DIR_LS}
${KIMI_AGENTS_MD}
${KIMI_SKILLS}
${KIMI_ADDITIONAL_DIRS_INFO}
```

可自定义变量：

```yaml
system_prompt_args:
  MY_VAR: "custom value"
```

然后在 prompt 里用：

```txt
${MY_VAR}
```

还支持 Jinja2 include：

```txt
{% include %}
```

官方说明 system prompt 是 Markdown 模板，支持 `${VAR}` 引用变量，并支持 Jinja2 `{% include %}` 引入其他文件。([Moonshot AI][1])

---

# 12. SubAgent：写在 Agent YAML 的 `subagents`

路径：

```txt
跟主 agent.yaml 放一起最省事，也可以任意路径，只要 path 能引用
```

主 Agent 文件里：

```yaml
agent:
  subagents:
    coder:
      path: ./coder-sub.yaml
      description: "Handle coding tasks"
    reviewer:
      path: ./reviewer-sub.yaml
      description: "Code review expert"
```

`subagents.<name>` 可用键：

```txt
path
description
```

SubAgent 文件本身也是标准 Agent YAML：

```yaml
version
agent
```

SubAgent 里可继续用：

```yaml
extend
name
system_prompt_path
system_prompt_args
tools
exclude_tools
subagents
```

但官方说明：默认内置 subagent 类型不能嵌套启动 Agent 工具，`Agent` 工具只给 root agent 使用；subagent 不能继续创建自己的 subagent。([Moonshot AI][1])

内置 subagent 类型：

```txt
coder
explore
plan
```

含义：

```txt
coder   = 通用软件工程，可读写文件、跑命令、搜索代码
explore = 只读快速探索，可搜索/读取/总结，不带写工具
plan    = 规划和架构设计，不带 Shell，不带写工具
```

SubAgent 通过 `Agent` 工具运行在隔离上下文，可以并行处理任务，并把结果返回给主 Agent；每个 subagent 实例在 session 目录下有独立上下文和元数据。([Moonshot AI][1])

---

# 13. AGENTS.md 项目规则

常见路径：

```txt
<project>\AGENTS.md
<project>\.kimi\AGENTS.md
<project>\frontend\AGENTS.md
<project>\backend\AGENTS.md
```

文件类型：

```txt
Markdown
```

可用键：

```txt
无固定 frontmatter
无 JSON
无 TOML
纯 Markdown
```

官方 Agent 模板变量里明确有 `${KIMI_AGENTS_MD}`，其含义是从项目根目录到当前工作目录合并后的 `AGENTS.md` 内容，并包括 `.kimi/AGENTS.md`。官方这块没有像 Codex/OpenCode 那样单独开一个 Rules 页面，所以这里按文档变量说明收敛，不替它脑补更多仪式。([Moonshot AI][1])

---

# 14. Skills：Kimi 专属路径

用户级 Kimi 专属路径：

```txt
%USERPROFILE%\.kimi\skills\<skill-name>\SKILL.md
```

项目级 Kimi 专属路径：

```txt
<project>\.kimi\skills\<skill-name>\SKILL.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.kimi\skills\my-skill -Force
notepad $env:USERPROFILE\.kimi\skills\my-skill\SKILL.md
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
type
```

值规则：

```txt
name = string，1-64 字符，小写字母/数字/连字符；可省略，默认目录名
description = string，1-1024 字符；可省略，会 fallback 到正文第一行
license = string
compatibility = string，最多 500 字符
metadata = object
type = "flow"   # 仅 flow skill 需要
```

普通 Skill 是“知识/流程说明”；Flow Skill 要在 frontmatter 写 `type: flow`，并在正文中放 Mermaid 或 D2 流程图，通过 `/flow:<name>` 调用。普通 Skill 可自动触发，也可手动 `/skill:<name>` 触发。([Moonshot AI][7])

---

# 15. Skills：通用/兼容路径

用户级通用推荐：

```txt
%USERPROFILE%\.config\agents\skills\<skill-name>\SKILL.md
```

用户级兼容：

```txt
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
```

用户级品牌兼容：

```txt
%USERPROFILE%\.claude\skills\<skill-name>\SKILL.md
%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md
```

项目级通用：

```txt
<project>\.agents\skills\<skill-name>\SKILL.md
```

项目级品牌兼容：

```txt
<project>\.claude\skills\<skill-name>\SKILL.md
<project>\.codex\skills\<skill-name>\SKILL.md
```

项目级 Kimi：

```txt
<project>\.kimi\skills\<skill-name>\SKILL.md
```

优先级：

```txt
Project > User > Extra > Built-in
```

用户级品牌组优先级：

```txt
~/.kimi/skills
> ~/.claude/skills
> ~/.codex/skills
```

用户级通用组优先级：

```txt
~/.config/agents/skills
> ~/.agents/skills
```

同名冲突时，Kimi 专属优先于 Claude / Codex；`merge_all_available_skills = true` 时会合并多个品牌目录。([Moonshot AI][7])

---

# 16. Extra Skills：`extra_skill_dirs`

路径：

```txt
%USERPROFILE%\.kimi\config.toml
```

配置键：

```toml
extra_skill_dirs
```

值类型：

```txt
extra_skill_dirs = array<string>
```

路径支持：

```txt
绝对路径
~ 开头路径
相对路径，相对于项目根目录
```

这些目录会作为 Extra scope 加入 Skills 发现；如果目录不存在会静默跳过。([Moonshot AI][7])

---

# 17. Flat Skill：直接 `.md` 文件

除了标准结构：

```txt
<skills-root>\<skill-name>\SKILL.md
```

Kimi 也识别：

```txt
<skills-root>\<skill-name>.md
```

规则：

```txt
文件名去掉 .md 作为 skill name
如果同名 flat .md 和目录同时存在，目录优先
description 解析顺序：
1. frontmatter description
2. 正文第一行，最多 240 字符
3. "No description provided."
```

这属于方便功能，但别滥用。Skill 一多，flat 文件最后会像满地散落的便利贴，找起来像考古。([Moonshot AI][7])

---

# 18. Plugins：本地插件目录

Plugin 是一个目录，核心文件：

```txt
<plugin-dir>\plugin.json
<plugin-dir>\config.json
<plugin-dir>\scripts\
```

安装方式：

```powershell
kimi plugin install C:\path\to\my-plugin
kimi plugin install my-plugin.zip
kimi plugin install https://github.com/user/repo.git
kimi plugin list
kimi plugin info my-plugin
kimi plugin remove my-plugin
```

`plugin.json` 可用键：

```json
name
version
description
config_file
inject
tools
```

值类型：

```txt
name = string，小写字母/数字/连字符
version = string，语义化版本
description = string
config_file = string path
inject = object
tools = array<object>
```

`tools[]` 可用键：

```txt
name
description
command
parameters
```

值类型：

```txt
tools[].name = string
tools[].description = string
tools[].command = array<string>
tools[].parameters = JSON Schema object
```

`inject` 支持变量：

```txt
api_key
base_url
```

Plugin 与 Skill 的区别：Skill 给模型读规则和流程，Plugin 则声明可执行工具，模型可以直接调用。Plugin 当前是 Beta，官方提醒配置定义未来可能变。([Moonshot AI][8])

---

# 19. Plugin Tool 脚本协议

脚本输入：

```txt
stdin: JSON object
```

脚本输出：

```txt
stdout: string
```

如果要结构化输出：

```txt
stdout: JSON text
```

也就是说，插件脚本接收 JSON 参数，从 stdout 返回结果；脚本语言可以是 Python、TypeScript、Shell 等，只要 `command` 能执行。([Moonshot AI][8])

---

# 20. 环境变量

Kimi provider 覆盖：

```txt
KIMI_BASE_URL
KIMI_API_KEY
KIMI_MODEL_NAME
KIMI_MODEL_MAX_CONTEXT_SIZE
KIMI_MODEL_CAPABILITIES
KIMI_MODEL_TEMPERATURE
KIMI_MODEL_TOP_P
KIMI_MODEL_MAX_TOKENS
KIMI_MODEL_THINKING_KEEP
```

OpenAI-compatible provider 覆盖：

```txt
OPENAI_BASE_URL
OPENAI_API_KEY
```

其他运行变量：

```txt
KIMI_SHARE_DIR
KIMI_CLI_NO_AUTO_UPDATE
KIMI_CLI_PASTE_CHAR_THRESHOLD
KIMI_CLI_PASTE_LINE_THRESHOLD
```

覆盖优先级：

```txt
环境变量 > CLI flags > 配置文件
```

官方说明：`KIMI_*` 只对 `kimi` provider 生效，`OPENAI_*` 对 `openai_legacy` / `openai_responses` 生效。([Moonshot AI][9])

---

# 21. CLI 配置覆盖

可用启动参数：

```txt
--config <TOML/JSON>
--config-file <PATH>
--model, -m <NAME>
--thinking
--no-thinking
--yolo
--yes
-y
--plan
--agent <NAME>
--agent-file <PATH>
--mcp-config-file <PATH>
--mcp-config <JSON>
--skills-dir <PATH>
```

说明：

```txt
--config 和 --config-file 不能同时使用
--model 必须引用 config.toml 里 models 已定义的模型
--plan 可让新会话或恢复会话进入 plan mode
--agent 选择内置 agent
--agent-file 加载自定义 YAML agent
--skills-dir 可指定额外 skills 目录，并可多次传入
```

这些参数分别来自配置覆盖、Agent、MCP、Skills 文档。([Moonshot AI][10])

---

# 22. 会话与 SubAgent 数据位置，不建议手改

主会话：

```txt
%USERPROFILE%\.kimi\sessions\<work-dir-hash>\<session-id>\
```

文件：

```txt
context.jsonl
wire.jsonl
state.json
```

SubAgent 实例：

```txt
%USERPROFILE%\.kimi\sessions\<work-dir-hash>\<session-id>\subagents\<agent_id>\
```

文件：

```txt
context.jsonl
wire.jsonl
meta.json
prompt.txt
output
```

`state.json` 会保存：

```txt
title
approval
plan_mode
plan_session_id
plan_slug
subagent_instances
additional_dirs
```

这些文件由 Kimi Code 自动管理，不建议手写。`context.jsonl` 第一行是冻结后的系统提示词，恢复会话时会复用，而不是重新生成。([Moonshot AI][2])

---

# 23. Plan 文件

路径：

```txt
%USERPROFILE%\.kimi\plans\<slug>.md
```

说明：

```txt
Plan mode 下的计划文件
由 state.json 的 plan_slug 关联
用 /plan clear 清理当前 plan session 文件
```

这个目录也属于运行数据，不建议你当配置文件手改，除非你很喜欢把自己变成同步冲突制造机。([Moonshot AI][2])

---

# 24. 最终速查表

```txt
# 主配置
%USERPROFILE%\.kimi\config.toml
键：default_model / default_thinking / default_yolo / default_plan_mode / default_editor / theme / show_thinking_stream / merge_all_available_skills / extra_skill_dirs / providers / models / loop_control / background / services / mcp / hooks

# MCP
%USERPROFILE%\.kimi\mcp.json
键：mcpServers；server 下 url / transport / headers / command / args / env

# Credentials
%USERPROFILE%\.kimi\credentials\<provider>.json
自动管理，不建议手改

# 自定义 Agent
任意路径\agent.yaml
加载：kimi --agent-file 任意路径\agent.yaml
键：version / agent.extend / agent.name / agent.system_prompt_path / agent.system_prompt_args / agent.tools / agent.exclude_tools / agent.subagents

# System Prompt
任意路径\system.md
由 agent.yaml 的 system_prompt_path 引用
变量：KIMI_NOW / KIMI_WORK_DIR / KIMI_WORK_DIR_LS / KIMI_AGENTS_MD / KIMI_SKILLS / KIMI_ADDITIONAL_DIRS_INFO / 自定义 system_prompt_args

# 项目规则
<project>\AGENTS.md
<project>\.kimi\AGENTS.md
<project>\<subdir>\AGENTS.md
键：无，纯 Markdown

# 用户级 Kimi Skill
%USERPROFILE%\.kimi\skills\<skill-name>\SKILL.md
键：name / description / license / compatibility / metadata / type

# 用户级通用 Skill
%USERPROFILE%\.config\agents\skills\<skill-name>\SKILL.md
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
键：name / description / license / compatibility / metadata / type

# 项目级 Skill
<project>\.kimi\skills\<skill-name>\SKILL.md
<project>\.agents\skills\<skill-name>\SKILL.md
键：name / description / license / compatibility / metadata / type

# Plugin
任意路径\my-plugin\plugin.json
安装：kimi plugin install 任意路径\my-plugin
键：name / version / description / config_file / inject / tools

# Hooks
%USERPROFILE%\.kimi\config.toml -> [[hooks]]
键：event / command / matcher / timeout

# Logs
%USERPROFILE%\.kimi\logs\kimi.log

# Sessions
%USERPROFILE%\.kimi\sessions\<work-dir-hash>\<session-id>\
自动管理，不建议手改
```

一句话定性：**Kimi Code 的可配置面比 Windsurf 强，尤其是 Agent / SubAgent 是官方明说支持的；但它不像 OpenCode 那样有固定 `agents/` 自动扫描目录，自定义 Agent 主要靠 `--agent-file` 加载。**Skills、MCP、Hooks、Plugins 都有，路径也还算清楚，除了 Agent 文件路径自由得像野生动物，剩下都能工程化落地。