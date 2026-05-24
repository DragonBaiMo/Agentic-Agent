你要的是 **Kiro CLI**，不是 Kiro IDE。下面这套只按 **Kiro CLI** 设计，避免再把 `.md SubAgent` 和 `.json CLI Agent` 混成一锅配置粥。Kiro CLI 的三层配置范围是：全局 `<user-home>/.kiro/`、项目 `<project-root>/.kiro`、Agent 配置 `<user-home | project-root>/.kiro/agents`；冲突优先级里，MCP 是 Agent > Project > Global，Prompts / Custom agents / Steering 都是 Project > Global。([Kiro][1])

# 1. 总体结构

推荐你在项目里这样搭：

```txt
your-project/
  .kiro/
    agents/
      sisyphus.json
      atlas.json
      explorer.json
      librarian.json
      reviewer.json
      implementer.json

    prompts/
      sisyphus.md
      atlas.md
      explorer.md
      librarian.md
      reviewer.md
      implementer.md

    settings/
      mcp.json

    steering/
      product.md
      tech.md
      structure.md
      coding-rules.md
      testing.md
      security.md

    skills/
      architecture-review/
        SKILL.md
        references/
      test-plan/
        SKILL.md
      prompt-optimization/
        SKILL.md
      frontend-quality/
        SKILL.md

    docs/
      agent-contract.md
```

全局目录建议这样放：

```txt
%USERPROFILE%\.kiro\
  agents\
    global-reviewer.json
    global-researcher.json

  prompts\
    global-review.md
    global-refactor.md

  settings\
    cli.json
    mcp.json

  steering\
    global-coding-rules.md
    global-output-rules.md

  skills\
    prompt-optimization\
      SKILL.md
    architecture-review\
      SKILL.md
```

对应关系：

```txt
.kiro/agents/*.json
= Kiro CLI 可切换 Agent；会出现在 /agent 列表里

.kiro/prompts/*
= @prompt-name 可调用的提示词模板

.kiro/settings/mcp.json
= 项目 MCP server 配置

.kiro/steering/*.md
= 项目长期规则，上下文基线

.kiro/skills/*/SKILL.md
= 可自动触发或 /skill-name 调用的 Agent Skill

%USERPROFILE%\.kiro\settings\cli.json
= Kiro CLI 全局设置
```

重点：**Kiro CLI 的自定义 Agent 必须是 `.json`。** 官方配置参考明确说 Agent configuration files are JSON files，文件名去掉 `.json` 会成为 agent 名；本地路径是 `.kiro/agents/`，全局路径是 `~/.kiro/agents/`，本地优先于全局。([Kiro][2])

# 2. 初始化命令

Windows PowerShell：

```powershell
# 项目级目录
mkdir .kiro\agents -Force
mkdir .kiro\prompts -Force
mkdir .kiro\settings -Force
mkdir .kiro\steering -Force
mkdir .kiro\skills -Force
mkdir .kiro\docs -Force

# 全局目录
mkdir $env:USERPROFILE\.kiro\agents -Force
mkdir $env:USERPROFILE\.kiro\prompts -Force
mkdir $env:USERPROFILE\.kiro\settings -Force
mkdir $env:USERPROFILE\.kiro\steering -Force
mkdir $env:USERPROFILE\.kiro\skills -Force
```

验证当前 CLI 能识别哪些 Agent：

```powershell
kiro-cli agent list
```

进入会话后也可以：

```txt
/agent
```

CLI 命令文档里，`kiro-cli agent list` 用于列可用 agents，`create` 创建 agent，`validate` 验证配置，`set-default` 设置默认 agent；`--agent` 是全局参数，可以启动时指定 custom agent。([Kiro][3])

# 3. CLI Settings：全局设置

路径：

```txt
%USERPROFILE%\.kiro\settings\cli.json
```

官方建议用 `kiro-cli settings` 命令配置，因为它会做校验；直接编辑也可以，但人类手写 JSON 的事故率高得像 JavaScript 日期 API。([Kiro][4])

推荐用命令配置：

```powershell
# 设置默认模型
kiro-cli settings chat.defaultModel claude-opus-4.7

# 设置默认 Agent
kiro-cli agent set-default sisyphus

# 开启 thinking tool
kiro-cli settings chat.enableThinking true

# 开启 todo list
kiro-cli settings chat.enableTodoList true

# 开启 checkpoint
kiro-cli settings chat.enableCheckpoint true

# 开启 knowledge
kiro-cli settings chat.enableKnowledge true

# 设置默认 include patterns
kiro-cli settings knowledge.defaultIncludePatterns '["*.md","*.ts","*.tsx","*.js","*.json","*.yaml","*.yml","*.py","*.java","*.kt","*.go","*.rs"]'

# 设置默认 exclude patterns
kiro-cli settings knowledge.defaultExcludePatterns '["node_modules",".git","dist","build",".next","target","*.log","*.lock"]'

# 禁止长会话自动压缩，按需开
kiro-cli settings chat.disableAutoCompaction false
```

Kiro CLI 模型页已经列出 `Claude Opus 4.7`，上下文窗口 1M，且官方给出的命令就是 `kiro-cli settings chat.defaultModel claude-opus-4.7`；模型页还说明可在 chat 里用 `/model set-current-as-default` 保存当前模型到 `~/.kiro/settings/cli.json`。([Kiro][5])

`cli.json` 里可直接写成扁平 key：

```json
{
  "chat.defaultModel": "claude-opus-4.7",
  "chat.defaultAgent": "sisyphus",
  "chat.enableThinking": true,
  "chat.enableTodoList": true,
  "chat.enableCheckpoint": true,
  "chat.enableKnowledge": true,
  "chat.disableAutoCompaction": false,
  "knowledge.defaultIncludePatterns": [
    "*.md",
    "*.ts",
    "*.tsx",
    "*.js",
    "*.json",
    "*.yaml",
    "*.yml",
    "*.py",
    "*.java",
    "*.kt",
    "*.go",
    "*.rs"
  ],
  "knowledge.defaultExcludePatterns": [
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "target",
    "*.log",
    "*.lock"
  ],
  "knowledge.maxFiles": 2000,
  "knowledge.chunkSize": 1024
}
```

查看所有可用设置：

```powershell
kiro-cli settings list --all
```

官方 Settings 文档也给了知识库、experimental features、性能调优、重置、打开 settings 文件等命令；数组值要用 JSON 格式，布尔值用小写 `true` / `false`。([Kiro][4])

# 4. MCP 配置

项目路径：

```txt
<project>\.kiro\settings\mcp.json
```

全局路径：

```txt
%USERPROFILE%\.kiro\settings\mcp.json
```

格式：

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {},
      "disabled": false,
      "disabledTools": []
    },
    "github": {
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {},
      "disabled": false,
      "disabledTools": []
    }
  }
}
```

Kiro CLI 的 MCP 配置是 JSON，顶层为 `mcpServers`；本地 server 用 `command`、`args`、`env`，远程 server 用 `url`、`headers`，并支持 `disabled` 和 `disabledTools`。([Kiro][6])

Agent 内部也可以配置 `mcpServers`，并且 `includeMcpJson: true` 会把全局和项目 `.kiro/settings/mcp.json` 一并注入当前 agent；官方说明 `includeMcpJson` 会包含 `~/.kiro/settings/mcp.json` 与 `<cwd>/.kiro/settings/mcp.json`。([Kiro][2])

# 5. Steering：长期规则

项目路径：

```txt
<project>\.kiro\steering\*.md
```

全局路径：

```txt
%USERPROFILE%\.kiro\steering\*.md
```

官方定义：Steering 是通过 `.kiro/steering/` 下的 Markdown 文件给 Kiro 持久项目知识，减少每次重复解释；项目级 steering 只作用于当前 workspace，全局 steering 作用于全部 workspace，冲突时项目级优先。([Kiro][7])

推荐 6 个文件：

```txt
.kiro/steering/product.md
.kiro/steering/tech.md
.kiro/steering/structure.md
.kiro/steering/coding-rules.md
.kiro/steering/testing.md
.kiro/steering/security.md
```

`product.md`：

```md
# Product Context

## Target
本项目是一个完整工程系统，不允许以 demo、mock-only、prototype-only 方式完成任务。

## Users
- 终端用户
- 管理员
- 开发维护者

## Product Rules
- UI 文案只服务终端用户理解和操作。
- 工程文档只服务开发者定位、修改、验证。
- Agent 输出必须围绕可执行结果，不输出空泛过程汇报。
```

`tech.md`：

```md
# Technology Stack

## Runtime
- Node.js / Python / Java / 其他：按项目实际补齐。

## Frontend
- Framework:
- Package manager:
- Build command:
- Test command:

## Backend
- Framework:
- API style:
- Database:
- Auth:

## Constraints
- 不新增未经确认的大型依赖。
- 不绕过既有架构边界。
- 不把临时实现伪装成完整系统。
```

`structure.md`：

```md
# Project Structure

## Source Layout
- frontend/: 前端应用
- backend/: 后端服务
- docs/: 文档
- tests/: 测试

## Import Rules
- 优先复用现有模块。
- 不跨层直接访问内部实现。
- 新增公共 API 必须说明调用方和兼容性。

## Change Boundary
- 修改前先定位调用链。
- 不修改无关文件。
- 迁移类改动必须给出回滚路径。
```

`coding-rules.md`：

```md
# Coding Rules

## General
- 先读现有实现，再修改。
- 保持最小改动。
- 遵循现有命名、错误处理、日志风格。
- 不添加无用抽象。
- 不把 TODO 当完成结果。

## Output
- 输出必须包含：变更文件、核心改动、验证命令、剩余风险。
```

`testing.md`：

```md
# Testing Rules

## Required
- 改业务逻辑后运行相关单元测试。
- 改接口后运行接口测试或最小调用验证。
- 改 UI 后说明人工或自动化验证路径。
- 测试失败时先报告失败原因，不得假装通过。

## Commands
- npm test
- npm run build
- pytest
- mvn test
```

`security.md`：

```md
# Security Rules

## Forbidden
- 不输出真实 secret。
- 不提交 .env、private key、token。
- 不绕过鉴权逻辑。
- 不删除安全校验来让测试通过。

## Required
- 涉及权限、登录、支付、数据删除时，必须说明风险和验证方式。
```

# 6. Skills：可复用能力包

项目路径：

```txt
<project>\.kiro\skills\<skill-name>\SKILL.md
```

全局路径：

```txt
%USERPROFILE%\.kiro\skills\<skill-name>\SKILL.md
```

Kiro CLI Skills 是可移植的 instruction package，遵循开放 Agent Skills 标准；Kiro 会先读取 `name` 和 `description`，自动匹配任务，或者把 Skill 暴露成 `/skill-name` slash command。项目级 `.kiro/skills/` 优先于全局 `~/.kiro/skills/`。([Kiro][8])

`SKILL.md` 必须有 YAML frontmatter：

```md
---
name: architecture-review
description: Use when reviewing architecture, module boundaries, API design, data flow, or long-term maintainability.
---

# Architecture Review Skill

## Steps
1. Identify the target feature or module.
2. Locate affected files and call chains.
3. Check module boundaries and coupling.
4. Identify risks, missing tests, and migration impact.
5. Output recommended changes and rejected alternatives.

## Output
- Scope
- Current structure
- Risks
- Options
- Recommended path
- Verification
```

推荐 Skills：

```txt
.kiro/skills/architecture-review/SKILL.md
.kiro/skills/test-plan/SKILL.md
.kiro/skills/prompt-optimization/SKILL.md
.kiro/skills/frontend-quality/SKILL.md
```

`test-plan/SKILL.md`：

```md
---
name: test-plan
description: Use when designing tests, validating changes, creating regression checks, or defining acceptance criteria.
---

# Test Plan Skill

## Steps
1. Identify changed behavior.
2. Locate existing test patterns.
3. Choose unit, integration, E2E, or manual validation.
4. Define minimum verification commands.
5. List remaining unverified risks.

## Output
- Changed behavior
- Required tests
- Commands
- Manual checks
- Remaining risks
```

`prompt-optimization/SKILL.md`：

```md
---
name: prompt-optimization
description: Use when rewriting prompts, instructions, agent prompts, rules, skills, SOPs, or AI collaboration documents.
---

# Prompt Optimization Skill

## Rules
- Preserve original intent.
- Remove self-talk.
- Identify the consumer.
- Keep context required for execution.
- Use technical specification style.
- Resolve ambiguity before rewriting when ambiguity blocks correctness.

## Output
- Optimized prompt
- Changed points
- Ambiguities requiring confirmation
```

# 7. Prompts：轻量复用模板

项目路径：

```txt
<project>\.kiro\prompts\
```

全局路径：

```txt
%USERPROFILE%\.kiro\prompts\
```

Kiro CLI prompt 系统支持 local prompts、global prompts、MCP prompts；local prompt 在 `.kiro/prompts/`，global prompt 在 `~/.kiro/prompts/`，优先级是 local > global > MCP。文件型 prompt 可用 `@prompt-name` 调用。([Kiro][9])

创建命令：

```txt
/prompts create --name code-review
/prompts edit code-review
/prompts list
/prompts details code-review
```

也可以直接建文件：

```txt
.kiro/prompts/code-review
.kiro/prompts/bug-analysis
.kiro/prompts/refactor-plan
```

`code-review`：

```txt
Review the current change set for correctness, security, maintainability, and missing tests.

Return:
1. Critical issues
2. Important issues
3. Minor issues
4. Required validation
5. Files that should not be changed
```

`bug-analysis`：

```txt
Analyze the reported bug.

Required output:
1. Reproduction path
2. Suspected call chain
3. Root cause candidates
4. Minimum fix
5. Regression tests
```

# 8. Custom Agent 总规则

CLI custom agent 是 `.json`，不是 `.md`。

路径：

```txt
# 项目级
<project>\.kiro\agents\<agent-name>.json

# 全局
%USERPROFILE%\.kiro\agents\<agent-name>.json
```

每个 Agent JSON 可以包含：`name`、`description`、`prompt`、`mcpServers`、`tools`、`toolAliases`、`allowedTools`、`toolsSettings`、`resources`、`hooks`、`includeMcpJson`、`model`、`keyboardShortcut`、`welcomeMessage`。([Kiro][2])

`prompt` 支持 inline，也支持 `file://` 指向外部 prompt 文件；相对路径按 agent JSON 文件所在目录解析。([Kiro][2])

`tools` 里内置工具可直接写名字，例如 `read`、`write`、`shell`；MCP 工具用 `@server_name` 或 `@server_name/tool_name`；`*` 表示所有内置与 MCP 工具，`@builtin` 表示全部内置工具。([Kiro][2])

`allowedTools` 是免确认工具，不等于可用工具；它支持精确匹配和 glob pattern，但不支持单独用 `"*"` 允许所有工具。官方还警告：允许 `write`、`shell` 或写能力 MCP 后，Agent 可修改其可访问文件，包括 `~/.kiro` 下的 skills、steering、MCP、agent 配置，所以别把权限开成游乐场。([Kiro][2])

# 9. 推荐 Agent 体系

## 9.1 sisyphus.json：主执行编排 Agent

路径：

```txt
.kiro/agents/sisyphus.json
```

```json
{
  "name": "sisyphus",
  "description": "Main execution and orchestration agent for controlled multi-step software development tasks.",
  "prompt": "file://../prompts/sisyphus.md",
  "model": "claude-opus-4.7",
  "includeMcpJson": true,
  "tools": ["read", "write", "shell", "code", "subagent", "@builtin"],
  "allowedTools": ["read"],
  "toolsSettings": {
    "write": {
      "allowedPaths": [
        "src/**",
        "frontend/**",
        "backend/**",
        "tests/**",
        "docs/**",
        "package.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "pyproject.toml"
      ]
    },
    "shell": {
      "allowedCommands": [
        "git status",
        "git diff",
        "git diff --stat",
        "npm test",
        "npm run test",
        "npm run build",
        "pnpm test",
        "pnpm build",
        "pytest",
        "mvn test",
        "gradle test"
      ],
      "deniedCommands": [
        "git push .*",
        "git commit .*",
        "rm -rf .*",
        "del /s .*",
        "format .*",
        "shutdown .*"
      ],
      "autoAllowReadonly": true
    },
    "subagent": {
      "availableAgents": ["explorer", "librarian", "reviewer", "implementer"],
      "trustedAgents": ["explorer", "reviewer"]
    }
  },
  "resources": [
    "file://AGENTS.md",
    "file://.kiro/steering/**/*.md",
    "skill://.kiro/skills/**/SKILL.md",
    {
      "type": "knowledgeBase",
      "source": "file://./docs",
      "name": "ProjectDocs",
      "description": "Project documentation and engineering notes",
      "indexType": "best",
      "autoUpdate": true
    }
  ],
  "hooks": {
    "agentSpawn": [
      {
        "command": "git status --short"
      }
    ],
    "preToolUse": [
      {
        "matcher": "execute_bash",
        "command": "echo Kiro CLI bash command requested"
      }
    ],
    "stop": [
      {
        "command": "git diff --stat"
      }
    ]
  },
  "keyboardShortcut": "ctrl+s",
  "welcomeMessage": "Sisyphus active: controlled implementation mode."
}
```

说明：`subagent.availableAgents` 可以限制可被 spawn 的 subagents，`trustedAgents` 可以让指定 agent 免每次确认；Kiro CLI subagents 文档明确给出 `availableAgents` 和 `trustedAgents` 用法，且支持 glob。([Kiro][10])

`resources` 支持 `file://`、`skill://` 和 knowledgeBase；`file://` 会启动时进入上下文，`skill://` 只加载 metadata、完整内容按需加载；knowledgeBase 支持 `type/source/name/description/indexType/autoUpdate`。([Kiro][2])

## 9.2 sisyphus.md

路径：

```txt
.kiro/prompts/sisyphus.md
```

```md
You are Sisyphus, the main execution and orchestration agent for this repository.

## Operating Mode

Work as the lead agent for controlled engineering tasks.

## Task Flow

1. Understand the request and identify the actual consumer of the deliverable.
2. Inspect existing files before editing.
3. Delegate exploration to explorer when file locations, call chains, or unknown structure matter.
4. Delegate external or documentation lookup to librarian when official docs, APIs, or sources matter.
5. Delegate review to reviewer before risky or broad changes.
6. Use implementer only for bounded implementation work.
7. Keep changes minimal and related to the current task.
8. Validate with existing tests, build commands, or explicit manual checks.

## Boundaries

- Do not modify unrelated files.
- Do not delete security checks to make tests pass.
- Do not claim validation succeeded unless a command or explicit inspection supports it.
- Do not hide uncertainty.

## Output

Return:
1. What changed
2. Files changed
3. Verification performed
4. Remaining risk
5. Next concrete action
```

## 9.3 explorer.json：只读代码探索 Agent

路径：

```txt
.kiro/agents/explorer.json
```

```json
{
  "name": "explorer",
  "description": "Read-only code exploration agent for locating files, call chains, symbols, module boundaries, and risk areas.",
  "prompt": "file://../prompts/explorer.md",
  "model": "claude-sonnet-4.6",
  "includeMcpJson": false,
  "tools": ["read", "code"],
  "allowedTools": ["read", "code"],
  "resources": [
    "file://AGENTS.md",
    "file://.kiro/steering/**/*.md"
  ],
  "welcomeMessage": "Explorer active: read-only code mapping mode."
}
```

## 9.4 explorer.md

```md
You are Explorer, a read-only repository mapping agent.

## Responsibilities

- Locate relevant files.
- Map call chains.
- Identify symbols, entry points, and dependencies.
- Report likely impact scope.

## Forbidden

- Do not edit files.
- Do not propose broad rewrites before locating evidence.
- Do not guess when the repository can be inspected.

## Output

- Relevant files
- Call chain
- Entry points
- Dependencies
- Risk areas
- Suggested next agent
```

## 9.5 librarian.json：文档 / MCP 检索 Agent

路径：

```txt
.kiro/agents/librarian.json
```

```json
{
  "name": "librarian",
  "description": "Documentation and external-source research agent for APIs, framework behavior, official docs, and reproducible references.",
  "prompt": "file://../prompts/librarian.md",
  "model": "claude-sonnet-4.6",
  "includeMcpJson": true,
  "tools": ["read", "@context7"],
  "allowedTools": ["read"],
  "resources": [
    "file://.kiro/steering/**/*.md",
    "skill://.kiro/skills/**/SKILL.md"
  ],
  "welcomeMessage": "Librarian active: source-grounded research mode."
}
```

## 9.6 librarian.md

```md
You are Librarian, a source-grounded research agent.

## Responsibilities

- Use official documentation first.
- Retrieve current API behavior through configured MCP tools.
- Distinguish facts from assumptions.
- Return actionable findings for implementation agents.

## Forbidden

- Do not implement code.
- Do not rely on memory for unstable technical facts.
- Do not cite irrelevant sources.

## Output

- Question answered
- Source-backed facts
- Implementation implications
- Risks or version constraints
- Links or source identifiers when available
```

## 9.7 reviewer.json：审查 Agent

路径：

```txt
.kiro/agents/reviewer.json
```

```json
{
  "name": "reviewer",
  "description": "Strict review agent for correctness, security, maintainability, edge cases, and missing tests.",
  "prompt": "file://../prompts/reviewer.md",
  "model": "claude-opus-4.7",
  "includeMcpJson": false,
  "tools": ["read", "code", "shell"],
  "allowedTools": ["read"],
  "toolsSettings": {
    "shell": {
      "allowedCommands": [
        "git status",
        "git diff",
        "git diff --stat",
        "npm test",
        "npm run test",
        "pytest"
      ],
      "deniedCommands": [
        "git push .*",
        "git commit .*",
        "rm -rf .*"
      ],
      "autoAllowReadonly": true
    }
  },
  "resources": [
    "file://AGENTS.md",
    "file://.kiro/steering/**/*.md",
    "skill://.kiro/skills/**/SKILL.md"
  ],
  "keyboardShortcut": "ctrl+r",
  "welcomeMessage": "Reviewer active: strict review mode."
}
```

## 9.8 reviewer.md

```md
You are Reviewer, a strict code and design review agent.

## Review Priorities

1. Correctness
2. Security
3. Data consistency
4. Edge cases
5. Test coverage
6. Maintainability
7. Unintended scope expansion

## Output

- Critical issues
- Important issues
- Minor issues
- Files involved
- Required fixes
- Required validation
```

## 9.9 implementer.json：实现 Agent

路径：

```txt
.kiro/agents/implementer.json
```

```json
{
  "name": "implementer",
  "description": "Bounded implementation agent for small, well-scoped code changes after exploration or planning.",
  "prompt": "file://../prompts/implementer.md",
  "model": "claude-sonnet-4.6",
  "includeMcpJson": true,
  "tools": ["read", "write", "shell", "code"],
  "allowedTools": ["read"],
  "toolsSettings": {
    "write": {
      "allowedPaths": [
        "src/**",
        "frontend/**",
        "backend/**",
        "tests/**",
        "docs/**",
        "package.json",
        "requirements.txt",
        "pyproject.toml"
      ]
    },
    "shell": {
      "allowedCommands": [
        "git status",
        "git diff",
        "npm test",
        "npm run test",
        "npm run build",
        "pnpm test",
        "pnpm build",
        "pytest"
      ],
      "deniedCommands": [
        "git push .*",
        "git commit .*",
        "rm -rf .*",
        "del /s .*"
      ],
      "autoAllowReadonly": true
    }
  },
  "resources": [
    "file://AGENTS.md",
    "file://.kiro/steering/**/*.md",
    "skill://.kiro/skills/**/SKILL.md"
  ],
  "keyboardShortcut": "ctrl+i",
  "welcomeMessage": "Implementer active: bounded implementation mode."
}
```

## 9.10 implementer.md

```md
You are Implementer, a bounded coding agent.

## Rules

- Only implement the requested change.
- Preserve existing architecture and style.
- Avoid broad refactors unless explicitly requested.
- Add or update tests when behavior changes.
- Run the smallest meaningful validation.

## Output

- Files changed
- Why each change was necessary
- Validation command and result
- Remaining risk
```

## 9.11 atlas.json：按既定计划执行 Agent

路径：

```txt
.kiro/agents/atlas.json
```

```json
{
  "name": "atlas",
  "description": "Plan-execution agent for implementing an existing explicit plan without redesigning the task.",
  "prompt": "file://../prompts/atlas.md",
  "model": "claude-sonnet-4.6",
  "includeMcpJson": true,
  "tools": ["read", "write", "shell", "code", "subagent"],
  "allowedTools": ["read"],
  "toolsSettings": {
    "subagent": {
      "availableAgents": ["explorer", "reviewer", "implementer"],
      "trustedAgents": ["explorer", "reviewer"]
    },
    "write": {
      "allowedPaths": [
        "src/**",
        "frontend/**",
        "backend/**",
        "tests/**",
        "docs/**"
      ]
    },
    "shell": {
      "allowedCommands": [
        "git status",
        "git diff",
        "npm test",
        "npm run build",
        "pytest"
      ],
      "deniedCommands": [
        "git push .*",
        "git commit .*",
        "rm -rf .*"
      ],
      "autoAllowReadonly": true
    }
  },
  "resources": [
    "file://AGENTS.md",
    "file://.kiro/steering/**/*.md",
    "skill://.kiro/skills/**/SKILL.md"
  ],
  "keyboardShortcut": "ctrl+a",
  "welcomeMessage": "Atlas active: plan execution mode."
}
```

## 9.12 atlas.md

```md
You are Atlas, a plan-execution agent.

## Rules

- Execute the existing plan.
- Do not redesign the plan unless it is internally inconsistent or impossible.
- Preserve the plan sequence.
- Mark blocked steps clearly.
- Validate each completed step.

## Output

- Completed steps
- Modified files
- Failed or blocked steps
- Validation
- Remaining plan items
```

# 10. SubAgent 调用方式

在 Sisyphus 会话里直接说：

```txt
让 explorer 先定位登录模块调用链，再让 reviewer 审查风险，最后让 implementer 做最小修复。
```

英文也能更稳：

```txt
Use the explorer agent to map the auth call chain, then use reviewer to identify risks, then use implementer for the smallest safe fix.
```

Kiro CLI 文档明确说：可以用自己的 agent config 作为 subagent，只要在分配任务时引用该 agent 名称；subagent 会继承该 agent 配置里的工具访问和设置。([Kiro][10])

限制也要记住：CLI subagent 目前可用 `read`、`write`、`shell`、`code` 和 MCP 工具；不可用 `web_search`、`web_fetch`、`introspect`、`thinking`、`todo_list`、`use_aws`、`grep`、`glob` 等普通 chat 工具。配置里包含不可用工具时，作为 subagent 运行时会不可用，但 agent 仍能运行。([Kiro][10])

查看 subagent 执行监控：

```txt
Ctrl+G
```

官方文档说 Ctrl+G 可打开 dedicated monitor，查看 subagent 状态、工具调用和输出。([Kiro][10])

# 11. Hooks

Kiro CLI Hooks 写在 **Agent JSON** 里，不是单独 `.kiro/hooks/*.json`。官方 Hooks 文档明确说 Hooks defined in the agent configuration file。([Kiro][11])

可用事件：

```json
{
  "hooks": {
    "agentSpawn": [
      {
        "command": "git status --short"
      }
    ],
    "userPromptSubmit": [
      {
        "command": "echo prompt submitted"
      }
    ],
    "preToolUse": [
      {
        "matcher": "execute_bash",
        "command": "echo bash requested"
      }
    ],
    "postToolUse": [
      {
        "matcher": "fs_write",
        "command": "git diff --stat"
      }
    ],
    "stop": [
      {
        "command": "git status --short"
      }
    ]
  }
}
```

配置参考列出的 hook 类型包括 `agentSpawn`、`userPromptSubmit`、`preToolUse`、`postToolUse`、`stop`；`preToolUse` 可在工具执行前触发，`postToolUse` 在执行后触发。([Kiro][2])

# 12. Resources

Agent JSON 的 `resources` 是 CLI 自定义 Agent 很关键的部分，不要全塞 prompt，不然上下文会像垃圾压缩车。

常用：

```json
{
  "resources": [
    "file://README.md",
    "file://.kiro/steering/**/*.md",
    "skill://.kiro/skills/**/SKILL.md",
    {
      "type": "knowledgeBase",
      "source": "file://./docs",
      "name": "ProjectDocs",
      "description": "Project documentation",
      "indexType": "best",
      "autoUpdate": true
    }
  ]
}
```

官方定义：`file://` 启动时直接加载进上下文；`skill://` 启动时只加载 metadata，完整内容按需加载；knowledge base 字段包括 `type`、`source`、`name`、`description`、`indexType`、`autoUpdate`。([Kiro][2])

建议规则：

```txt
file://AGENTS.md
= 只放核心项目规则

file://.kiro/steering/**/*.md
= 让 Agent 读取项目约束

skill://.kiro/skills/**/SKILL.md
= 技能按需加载，不污染上下文

knowledgeBase
= 大文档、大设计稿、大历史资料
```

# 13. 启动与验证流程

创建文件后，跑：

```powershell
kiro-cli agent list
```

验证单个 Agent：

```powershell
kiro-cli agent validate .kiro\agents\sisyphus.json
kiro-cli agent validate .kiro\agents\explorer.json
kiro-cli agent validate .kiro\agents\reviewer.json
```

启动指定 Agent：

```powershell
kiro-cli chat --agent sisyphus
```

进入会话后：

```txt
/agent
```

你应该看到：

```txt
sisyphus
atlas
explorer
librarian
reviewer
implementer
kiro_default
kiro_guide
kiro_planner
```

如果看不到，按这个查：

```powershell
# 是否真的存在 JSON
dir .kiro\agents
dir $env:USERPROFILE\.kiro\agents

# 是否 JSON 语法坏了
kiro-cli agent validate .kiro\agents\sisyphus.json

# 是否在项目目录或其子目录启动
pwd

# 是否 agent name 和文件名冲突
kiro-cli agent list
```

`/agent` 是切换 agent，`/plan` 才是进入 plan mode，`Shift+Tab` 也是进入 Plan mode；Terminal UI 文档把这三个命令分得很清楚：`/plan` 进入 plan mode，`/agent` 切换 agents。([Kiro][12])

# 14. 推荐使用节奏

常规开发：

```powershell
kiro-cli chat --agent sisyphus
```

提示：

```txt
先让 explorer 定位用户管理模块调用链，再由 reviewer 审查风险，最后由 implementer 做最小修复。不要改无关文件。
```

只做审查：

```powershell
kiro-cli chat --agent reviewer
```

提示：

```txt
Review the current git diff. Focus on correctness, security, data consistency, and missing tests.
```

按计划执行：

```powershell
kiro-cli chat --agent atlas
```

提示：

```txt
Execute the plan in .kiro/specs/user-auth/tasks.md. Do not redesign the plan unless blocked.
```

文档/API 核对：

```powershell
kiro-cli chat --agent librarian
```

提示：

```txt
Use configured MCP documentation sources to verify the current API behavior before implementation.
```

# 15. 最终关键区别表

| 文件                          |              Kiro CLI 是否读取 | 用途                   | 格式              |
| --------------------------- | -------------------------: | -------------------- | --------------- |
| `.kiro/agents/*.json`       |                          是 | CLI 可切换 Custom Agent | JSON            |
| `~/.kiro/agents/*.json`     |                          是 | 全局 CLI Custom Agent  | JSON            |
| `.kiro/agents/*.md`         | 否，CLI `/agent` 不当主 Agent 用 | IDE Custom SubAgent  | Markdown + YAML |
| `.kiro/settings/mcp.json`   |                          是 | 项目 MCP               | JSON            |
| `~/.kiro/settings/mcp.json` |                          是 | 全局 MCP               | JSON            |
| `~/.kiro/settings/cli.json` |                          是 | CLI 全局设置             | JSON            |
| `.kiro/steering/*.md`       |                          是 | 项目长期规则               | Markdown        |
| `~/.kiro/steering/*.md`     |                          是 | 全局长期规则               | Markdown        |
| `.kiro/skills/*/SKILL.md`   |                          是 | 项目 Skill             | Markdown + YAML |
| `~/.kiro/skills/*/SKILL.md` |                          是 | 全局 Skill             | Markdown + YAML |
| `.kiro/prompts/*`           |                          是 | 项目 prompt            | 文本              |
| `~/.kiro/prompts/*`         |                          是 | 全局 prompt            | 文本              |

# 16. 一句话版本

Kiro CLI 正确体系是：

```txt
CLI 主 Agent / 可切换 Agent
= .kiro/agents/*.json

Agent Prompt
= .kiro/prompts/*.md，通过 prompt: file:// 引用

长期项目规则
= .kiro/steering/*.md

能力包
= .kiro/skills/*/SKILL.md

外部工具
= .kiro/settings/mcp.json

全局偏好
= ~/.kiro/settings/cli.json
```

你之前卡住，是因为 `.md` 只适合 Kiro IDE Custom SubAgent，**不会出现在 Kiro CLI 的 `/agent` 可切换主 Agent 列表里**。CLI 要 `.json`。这个坑现在可以封棺了，别再让 Kiro 那套双格式设计继续浪费你的脑细胞。

[1]: https://kiro.dev/docs/cli/chat/configuration/ "Configuration - CLI - Docs - Kiro"
[2]: https://kiro.dev/docs/cli/custom-agents/configuration-reference/ "Agent configuration reference - CLI - Docs - Kiro"
[3]: https://kiro.dev/docs/cli/reference/cli-commands/ "CLI commands - CLI - Docs - Kiro"
[4]: https://kiro.dev/docs/cli/reference/settings/ "Settings - CLI - Docs - Kiro"
[5]: https://kiro.dev/docs/cli/models/ "Models - CLI - Docs - Kiro"
[6]: https://kiro.dev/docs/cli/mcp/configuration/ "Configuration - CLI - Docs - Kiro"
[7]: https://kiro.dev/docs/cli/steering/ "Steering - CLI - Docs - Kiro"
[8]: https://kiro.dev/docs/cli/skills/ "Agent Skills - CLI - Docs - Kiro"
[9]: https://kiro.dev/docs/cli/chat/manage-prompts/ "Manage prompts - CLI - Docs - Kiro"
[10]: https://kiro.dev/docs/cli/chat/subagents/ "Subagents - CLI - Docs - Kiro"
[11]: https://kiro.dev/docs/cli/hooks/ "Hooks - CLI - Docs - Kiro"
[12]: https://kiro.dev/docs/cli/terminal-ui/ "Terminal UI - CLI - Docs - Kiro"
