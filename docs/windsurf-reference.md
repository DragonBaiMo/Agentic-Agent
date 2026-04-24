# 0. 总路径速览，Windows

```txt
# Windsurf / Codeium 全局配置根目录
%USERPROFILE%\.codeium\windsurf\

# 全局 Rules
%USERPROFILE%\.codeium\windsurf\memories\global_rules.md

# 全局 Skills
%USERPROFILE%\.codeium\windsurf\skills\<skill-name>\SKILL.md

# 兼容 Agent Skills 路径
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md

# 全局 Workflows
%USERPROFILE%\.codeium\windsurf\global_workflows\<workflow-name>.md

# 全局 MCP
%USERPROFILE%\.codeium\windsurf\mcp_config.json

# 全局 Hooks
%USERPROFILE%\.codeium\windsurf\hooks.json

# 全局 Ignore
%USERPROFILE%\.codeium\.codeiumignore

# Windsurf 编辑器 settings.json，偏 VS Code 系，不是 Cascade 专属
%APPDATA%\Windsurf\User\settings.json
```

工作区路径：

```txt
# 工作区 Rules
<project>\.windsurf\rules\*.md

# 工作区 Skills
<project>\.windsurf\skills\<skill-name>\SKILL.md

# 兼容 Agent Skills 路径
<project>\.agents\skills\<skill-name>\SKILL.md

# 工作区 Workflows
<project>\.windsurf\workflows\<workflow-name>.md

# 工作区 Hooks
<project>\.windsurf\hooks.json

# 目录级 Cascade 指令
<project>\AGENTS.md
<project>\frontend\AGENTS.md
<project>\backend\AGENTS.md

# 工作区 Ignore
<project>\.codeiumignore
```

企业/系统级路径，Windows：

```txt
C:\ProgramData\Windsurf\rules\*.md
C:\ProgramData\Windsurf\skills\<skill-name>\SKILL.md
C:\ProgramData\Windsurf\workflows\*.md
C:\ProgramData\Windsurf\hooks.json
```

Windsurf 官方文档明确列出了 Rules、Skills、Workflows、Hooks 的 global/workspace/system 路径；MCP 主配置是 `~/.codeium/windsurf/mcp_config.json`；`.codeiumignore` 支持全局 `~/.codeium/.codeiumignore` 和仓库级 `.codeiumignore`。([Windsurf Docs][2])

---

# 1. 全局 Rules

路径：

```txt
%USERPROFILE%\.codeium\windsurf\memories\global_rules.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.codeium\windsurf\memories -Force
notepad $env:USERPROFILE\.codeium\windsurf\memories\global_rules.md
```

文件类型：

```txt
Markdown
```

可用“键值”：

```txt
无固定 frontmatter
无 YAML
无 JSON
纯 Markdown
始终生效 always-on
单文件上限：6000 字符
```

可写结构：

```md
# Global Rules

## Coding Rules
## Output Rules
## Security Rules
## Forbidden Actions
## Testing Rules
```

说明：`global_rules.md` 是 always-on，全局所有 workspace 都生效；官方说它不使用 frontmatter。([Windsurf Docs][2])

---

# 2. 工作区 Rules

路径：

```txt
<project>\.windsurf\rules\*.md
```

怎么配：

```powershell
mkdir .windsurf\rules -Force
notepad .windsurf\rules\backend.md
```

文件类型：

```txt
Markdown + YAML frontmatter
```

可用 frontmatter 键：

```yaml
trigger
description
globs
```

`trigger` 可用值：

```txt
always_on
model_decision
glob
manual
```

键值说明：

```txt
trigger = always_on
# 每次对话都完整加入 Cascade system prompt

trigger = model_decision
description = string
# 默认只把 description 给 Cascade；Cascade 判断相关时再读取完整规则

trigger = glob
globs = string
# Cascade 读/改匹配文件时触发

trigger = manual
# 默认不进入上下文；输入 @rule-name 手动触发
```

文件限制：

```txt
每个 workspace rule 文件上限：12000 字符
```

说明：Windsurf 官方列出四种 activation modes：`always_on`、`model_decision`、`glob`、`manual`；workspace rule 用 frontmatter 的 `trigger` 字段声明触发模式。([Windsurf Docs][2])

---

# 3. 系统级 Rules，企业/管理员

Windows 路径：

```txt
C:\ProgramData\Windsurf\rules\*.md
```

怎么配：

```powershell
mkdir "C:\ProgramData\Windsurf\rules" -Force
notepad "C:\ProgramData\Windsurf\rules\security.md"
```

文件类型：

```txt
Markdown
```

可用键：

```txt
和普通 Rules 类似，但通常作为企业强制基线
.md 文件会被自动加载
普通用户不可删除
```

说明：官方给出的系统级 Rules Windows 路径是 `C:\ProgramData\Windsurf\rules\*.md`，用于组织级规则。([Windsurf Docs][2])

---

# 4. AGENTS.md

路径：

```txt
<project>\AGENTS.md
<project>\agents.md

<project>\frontend\AGENTS.md
<project>\backend\AGENTS.md
<project>\docs\AGENTS.md
```

怎么配：

```powershell
notepad AGENTS.md
notepad frontend\AGENTS.md
```

文件类型：

```txt
Markdown
```

可用“键值”：

```txt
无 frontmatter
无 YAML
无 JSON
纯 Markdown
```

作用域规则：

```txt
根目录 AGENTS.md
= always-on，作用于整个 workspace

子目录 AGENTS.md
= 自动 glob，该目录及其子目录生效

AGENTS.md / agents.md
= 大小写不敏感，都会识别
```

说明：Windsurf 会自动发现 workspace 内的 `AGENTS.md` 或 `agents.md`，根目录按 always-on 处理，子目录按 `<directory>/**` 自动作用域处理。([Windsurf Docs][1])

---

# 5. 全局 Skills

路径：

```txt
%USERPROFILE%\.codeium\windsurf\skills\<skill-name>\SKILL.md
```

兼容路径：

```txt
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
```

如果启用了 Claude Code config reading，还会扫描：

```txt
%USERPROFILE%\.claude\skills\<skill-name>\SKILL.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.codeium\windsurf\skills\my-skill -Force
notepad $env:USERPROFILE\.codeium\windsurf\skills\my-skill\SKILL.md
```

文件类型：

```txt
Markdown + YAML frontmatter
```

必填 frontmatter：

```yaml
name
description
```

可用键值：

```txt
name = string
description = string
```

目录内可放任意支持文件：

```txt
SKILL.md
*.md
*.yaml
*.json
*.sh
*.py
templates/
references/
scripts/
assets/
```

调用方式：

```txt
自动触发：Cascade 根据 description 判断
手动触发：@skill-name
```

说明：Windsurf Skills 是文件夹结构，必须有 `SKILL.md`，frontmatter 必填 `name` 和 `description`；全局路径是 `~/.codeium/windsurf/skills/`，同时也发现 `.agents/skills/` 和 `~/.agents/skills/`。([Windsurf Docs][3])

---

# 6. 工作区 Skills

路径：

```txt
<project>\.windsurf\skills\<skill-name>\SKILL.md
```

兼容路径：

```txt
<project>\.agents\skills\<skill-name>\SKILL.md
```

怎么配：

```powershell
mkdir .windsurf\skills\code-review -Force
notepad .windsurf\skills\code-review\SKILL.md
```

可用键值同全局 Skills：

```yaml
name
description
```

说明：Workspace Skills 只在当前 workspace 可用，适合提交到项目仓库；结构和全局 Skills 一样。([Windsurf Docs][3])

---

# 7. 系统级 Skills，企业/管理员

Windows 路径：

```txt
C:\ProgramData\Windsurf\skills\<skill-name>\SKILL.md
```

怎么配：

```powershell
mkdir "C:\ProgramData\Windsurf\skills\company-review" -Force
notepad "C:\ProgramData\Windsurf\skills\company-review\SKILL.md"
```

可用键：

```yaml
name
description
```

说明：官方给出的 Windows 系统级 Skills 路径是 `C:\ProgramData\Windsurf\skills\`，每个 skill 仍然是一个含 `SKILL.md` 的子目录。([Windsurf Docs][3])

---

# 8. 全局 Workflows

路径：

```txt
%USERPROFILE%\.codeium\windsurf\global_workflows\<workflow-name>.md
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.codeium\windsurf\global_workflows -Force
notepad $env:USERPROFILE\.codeium\windsurf\global_workflows\review-pr.md
```

文件类型：

```txt
Markdown
```

可用“键值”：

```txt
无强制 YAML frontmatter
无 JSON
纯 Markdown
```

常见结构：

```md
## /workflow-name

一句描述

1. Step one
2. Step two
3. Step three
```

调用方式：

```txt
/workflow-name
```

限制：

```txt
手动触发，不会自动触发
单文件上限：12000 字符
```

说明：Workflows 是手动 slash command，只能通过 `/[workflow-name]` 调用；全局路径是 `~/.codeium/windsurf/global_workflows/*.md`。([Windsurf Docs][4])

---

# 9. 工作区 Workflows

路径：

```txt
<project>\.windsurf\workflows\<workflow-name>.md
```

怎么配：

```powershell
mkdir .windsurf\workflows -Force
notepad .windsurf\workflows\run-tests-and-fix.md
```

可用键：

```txt
无固定键值
Markdown 内容即流程定义
```

发现规则：

```txt
当前 workspace 内所有 .windsurf/workflows/
Git 仓库中会向上搜索到 git root
多 workspace 会去重
```

优先级：

```txt
System > Workspace > Global > Built-in
```

说明：Windsurf 会发现当前 workspace、子目录以及 Git root 父级范围内的 `.windsurf/workflows/`；同名 workflow 时系统级最高，其次 workspace，再到 global，最后 built-in。([Windsurf Docs][4])

---

# 10. 系统级 Workflows，企业/管理员

Windows 路径：

```txt
C:\ProgramData\Windsurf\workflows\*.md
```

怎么配：

```powershell
mkdir "C:\ProgramData\Windsurf\workflows" -Force
notepad "C:\ProgramData\Windsurf\workflows\security-scan.md"
```

可用键：

```txt
无固定键值
Markdown 内容即 workflow
```

说明：系统级 Workflows 从 OS-specific 目录加载，Windows 是 `C:\ProgramData\Windsurf\workflows\*.md`。([Windsurf Docs][4])

---

# 11. MCP 配置

路径：

```txt
%USERPROFILE%\.codeium\windsurf\mcp_config.json
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.codeium\windsurf -Force
notepad $env:USERPROFILE\.codeium\windsurf\mcp_config.json
```

也可以从 UI 打开：

```txt
Cascade 面板右上角 MCPs 图标
或 Windsurf Settings > Cascade > MCP Servers
然后编辑 raw mcp_config.json
```

顶层键：

```json
mcpServers
```

STDIO server 可用键：

```json
{
  "mcpServers": {
    "<server-id>": {
      "command": "string",
      "args": ["string"],
      "env": {
        "KEY": "VALUE"
      }
    }
  }
}
```

HTTP / Remote server 可用键：

```json
{
  "mcpServers": {
    "<server-id>": {
      "serverUrl": "string",
      "url": "string",
      "headers": {
        "KEY": "VALUE"
      }
    }
  }
}
```

常见可用字段汇总：

```txt
mcpServers = object

mcpServers.<id>.command = string
mcpServers.<id>.args = array<string>
mcpServers.<id>.env = object<string,string>

mcpServers.<id>.serverUrl = string
mcpServers.<id>.url = string
mcpServers.<id>.headers = object<string,string>
```

支持变量插值的字段：

```txt
command
args
env
serverUrl
url
headers
```

插值语法：

```txt
${env:VAR_NAME}
${file:/path/to/file}
```

支持传输：

```txt
stdio
Streamable HTTP
SSE
```

说明：官方 MCP 文档明确 `mcp_config.json` 在 `~/.codeium/windsurf/mcp_config.json`，顶层为 `mcpServers`；远程 HTTP MCP 用 `serverUrl` 或 `url`；支持 `command`、`args`、`env`、`serverUrl`、`url`、`headers` 字段插值。([Windsurf Docs][5])

---

# 12. Hooks，全局

路径：

```txt
%USERPROFILE%\.codeium\windsurf\hooks.json
```

怎么配：

```powershell
notepad $env:USERPROFILE\.codeium\windsurf\hooks.json
```

顶层键：

```json
hooks
```

Hook event 可用键：

```txt
pre_read_code
post_read_code
pre_write_code
post_write_code
pre_run_command
post_run_command
pre_mcp_tool_use
post_mcp_tool_use
pre_user_prompt
post_cascade_response
post_cascade_response_with_transcript
post_setup_worktree
```

每个 hook 对象可用键：

```json
{
  "command": "string",
  "powershell": "string",
  "show_output": true,
  "working_directory": "string"
}
```

字段说明：

```txt
command = macOS/Linux 用 bash -c 执行；Windows 没有 powershell 时会 fallback
powershell = Windows 用 powershell -Command 执行
show_output = 是否在 Cascade UI 显示 stdout/stderr
working_directory = 执行目录，默认 workspace root
```

阻断规则：

```txt
pre_* hook 退出码 2 可以阻断动作
post_* hook 不能阻断，因为动作已经发生
```

Hooks 合并顺序：

```txt
System → User → Workspace
```

说明：Hooks 有 system/user/workspace 三层，Windsurf IDE 用户级路径是 `~/.codeium/windsurf/hooks.json`，workspace 路径是 `.windsurf/hooks.json`；hook 对象支持 `command`、`powershell`、`show_output`、`working_directory`。([Windsurf Docs][6])

---

# 13. Hooks，工作区

路径：

```txt
<project>\.windsurf\hooks.json
```

怎么配：

```powershell
notepad .windsurf\hooks.json
```

可用键同全局 Hooks：

```json
hooks
```

事件同上：

```txt
pre_read_code
post_read_code
pre_write_code
post_write_code
pre_run_command
post_run_command
pre_mcp_tool_use
post_mcp_tool_use
pre_user_prompt
post_cascade_response
post_cascade_response_with_transcript
post_setup_worktree
```

说明：workspace hook 适合提交到项目仓库，执行顺序在 system 和 user 之后。([Windsurf Docs][6])

---

# 14. Hooks，系统级/企业

Windows 路径：

```txt
C:\ProgramData\Windsurf\hooks.json
```

怎么配：

```powershell
notepad "C:\ProgramData\Windsurf\hooks.json"
```

可用键同上。

说明：系统级 Hooks 用于组织策略，Windows 路径是 `C:\ProgramData\Windsurf\hooks.json`。([Windsurf Docs][6])

---

# 15. Ignore，全局

路径：

```txt
%USERPROFILE%\.codeium\.codeiumignore
```

怎么配：

```powershell
mkdir $env:USERPROFILE\.codeium -Force
notepad $env:USERPROFILE\.codeium\.codeiumignore
```

文件类型：

```txt
gitignore 语法
```

可写规则：

```gitignore
node_modules/
dist/
.env
*.pem
*.key
```

说明：全局 `.codeiumignore` 放在 `~/.codeium/`，适用于所有 Windsurf workspace，语法和 `.gitignore` 相同。([Windsurf Docs][7])

---

# 16. Ignore，工作区

路径：

```txt
<project>\.codeiumignore
```

怎么配：

```powershell
notepad .codeiumignore
```

可用语法：

```txt
.gitignore 同款语法
```

说明：工作区 `.codeiumignore` 用于配置 Windsurf Indexing 忽略文件；被忽略文件不会被索引。([Windsurf Docs][7])

---

# 17. Windsurf 编辑器 settings.json，非 Cascade 专属

路径，Windows：

```txt
%APPDATA%\Windsurf\User\settings.json
```

打开方式：

```txt
Windsurf Settings
或 Command Palette → Open Windsurf Settings Page
或普通 Settings UI 右上角打开 settings.json
```

说明：这个文件偏编辑器/VS Code 系配置，例如 marketplace、UI、扩展、编辑器行为等；Windsurf 官方高级配置文档更推荐通过 Windsurf Settings 页面改，普通 Agent/Cascade 能力不主要走这个文件。([Windsurf Docs][8])

这个文件键太多，属于 VS Code-family 设置体系，不建议把 Cascade Rules/Skills/MCP/Hook 乱塞进去。Windsurf 的 Cascade 可编程配置主要还是前面那些专用路径。

---

# 18. 最终速查表

```txt
# 全局规则
%USERPROFILE%\.codeium\windsurf\memories\global_rules.md
键：无 frontmatter，纯 Markdown，always-on

# 工作区规则
<project>\.windsurf\rules\*.md
键：trigger / description / globs

# 目录规则
<project>\AGENTS.md
<project>\<subdir>\AGENTS.md
键：无 frontmatter，纯 Markdown，按目录自动作用域

# 全局 Skill
%USERPROFILE%\.codeium\windsurf\skills\<skill-name>\SKILL.md
键：name / description

# 兼容 Skill
%USERPROFILE%\.agents\skills\<skill-name>\SKILL.md
键：name / description

# 工作区 Skill
<project>\.windsurf\skills\<skill-name>\SKILL.md
键：name / description

# 全局 Workflow
%USERPROFILE%\.codeium\windsurf\global_workflows\<workflow-name>.md
键：无固定键值，Markdown，/workflow-name 调用

# 工作区 Workflow
<project>\.windsurf\workflows\<workflow-name>.md
键：无固定键值，Markdown，/workflow-name 调用

# MCP
%USERPROFILE%\.codeium\windsurf\mcp_config.json
键：mcpServers；server 下 command/args/env 或 serverUrl/url/headers

# 全局 Hooks
%USERPROFILE%\.codeium\windsurf\hooks.json
键：hooks；事件名；command/powershell/show_output/working_directory

# 工作区 Hooks
<project>\.windsurf\hooks.json
键：同上

# 全局 Ignore
%USERPROFILE%\.codeium\.codeiumignore
键：无，gitignore 语法

# 工作区 Ignore
<project>\.codeiumignore
键：无，gitignore 语法
```

重点别搞错：**Windsurf 没有像 Codex 那样的全局 `agents/*.toml` 自定义 Agent 文件。**
它的“可配置核心”是：

```txt
Rules / AGENTS.md
= 行为约束

Skills
= 可自动/手动调用的复杂任务能力包

Workflows
= 手动 slash 流程

MCP
= 外部工具接入

Hooks
= 生命周期拦截/审计/自动化

.codeiumignore
= 索引排除
```