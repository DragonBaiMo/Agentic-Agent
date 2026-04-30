---
name: skill-create
description: 创建或更新 AgentSkill。用于设计、编写、打包包含脚本/引用文档/资源的 Skill。适用场景：(1) 从零创建新 Skill (2) 更新/重构已有 Skill (3) 审查 Skill 质量 (4) 打包 Skill 用于分发。触发词："创建 skill"、"写个 skill"、"更新 skill"、"skill 质量检查"、"打包 skill"。
---

# Skill Create — 操作手册

> 目标：当用户说"帮我写个 skill"时，AI 必须能**完整产出**一个结构正确、内容不打架、可直接使用的 Skill。

---

## 什么是 Skill

Skill 是模块化的能力包，给 AI 装上特定领域的操作知识。

目录结构：

```
skill-name/
├── SKILL.md              （必须：唯一入口文件）
├── scripts/              （可选：可执行脚本）
├── references/           （可选：按需加载的补充文档）
└── assets/               （可选：模板/图片等输出资源）
```

每个部分的定位：

| 部分 | 是什么 | 什么时候加载 | 放什么 |
|------|--------|-------------|--------|
| SKILL.md frontmatter | 触发器 | 始终在上下文 | name + description（~100 词） |
| SKILL.md 正文 | 操作手册 | Skill 被触发时 | 完整流程或骨架导航 |
| scripts/ | 工具箱 | 执行时调用，不读入上下文 | 确定性代码、重复逻辑 |
| references/ | 补充手册 | AI 判断需要时才读 | 细节文档、schema、API 参考 |
| assets/ | 素材库 | 不读入上下文，用于输出 | 模板、图片、字体、样板代码 |

**不要创建的文件：** README.md、CHANGELOG.md、INSTALLATION_GUIDE.md 等。Skill 是给 AI 用的操作手册，不是人类文档项目。

### Token 成本模型（核心心智模型）

Skill 的加载是**分层按需**的，每一层有不同的 Token 成本：

| 层 | 何时加载 | Token 预算 | 关键原则 |
|---|---------|-----------|----------|
| **description** | 始终在上下文 | ~100 词 | 只写触发信息——做什么 + 什么时候用 |
| **SKILL.md 正文** | 被 description 触发后 | 几百行 | 不重复 description 已说的触发条件（AI 读到正文时已被触发） |
| **references/** | AI 判断需要时 | 不限 | 不写"入口条件/前置条件"（AI 已进入才能读到，写了 = 废话） |

**反模式**：
- 正文里写"触发条件"段 → 与 description 重复，AI 已触发才读正文
- reference 里写"入口条件" → AI 已进入该文件才能读到，纯冗余
- reference 里写"导航段"（返回 SKILL.md / 前后链接） → SKILL.md 已是导航中枢，reference 内重复 = 浪费
- SKILL.md 与 reference 重复同一内容 → 两处措辞必然有差异，导致执行歧义

---

## 一套完整流程（按顺序执行）

### Step 1）理解需求

跳过条件：用户已经给出了清晰的功能描述和使用场景。

与用户确认：
- 这个 Skill 要解决什么问题？
- 给几个具体的使用场景？（"用户会说什么话来触发它？"）
- 有没有现成的脚本/文档/模板可以复用？

不要一次问太多，先问最关键的，按需跟进。

**产出：** 对 Skill 功能范围和触发场景的清晰认知。

---

### Step 2）规划内容

对每个使用场景分析：
1. 从零执行需要哪些步骤？
2. 哪些步骤每次都一样？（→ 考虑做成 script）
3. 哪些信息每次都要查？（→ 考虑做成 reference）
4. 哪些文件每次都要用？（→ 考虑放 assets）

示例判断：

| 场景 | 分析 | 放哪 |
|------|------|------|
| 每次都要写同样的 PDF 旋转代码 | 重复代码 | `scripts/rotate_pdf.py` |
| 每次都要查数据库 schema | 重复查询 | `references/schema.md` |
| 每次都要用同一套前端模板 | 重复素材 | `assets/hello-world/` |
| 每次流程都不太一样，靠判断 | 灵活决策 | 写在 SKILL.md 正文里 |

**产出：** 一份资源清单——哪些 scripts、哪些 references、哪些 assets。

---

### Step 3）选择 Skill 类型（关键决策）

在写任何内容之前，先选类型。这个决策决定了 SKILL.md 和 references 之间的主从关系。

#### Type A：主流程型（默认）

**SKILL.md 是主体，references 是配角。**

读 SKILL.md 就能完成工作。references 只在遇到特定复杂节点时才需要查阅。

选择条件：
- 工作流线性、自包含
- 大多数用户需要完整流程
- 总量可控

实际例子——一个 API 调用 Skill：

```markdown
# SKILL.md 写：
步骤 3：调用 API 获取数据
- 使用 Bearer Token 认证
- 端点：POST /api/v2/query
- 请求体格式：{"query": "...", "limit": 100}
- 若需要 OAuth2 握手细节，读取 references/api-auth.md

# references/api-auth.md 写：
- OAuth2 完整握手流程
- Token 刷新机制
- 错误码与重试策略
```

SKILL.md 告诉你"做什么、怎么做"。reference 只在你需要深挖某个环节时才读。

#### Type B：极简主文件型

**SKILL.md 是导航地图，references 是实际内容。**

SKILL.md 告诉你"去哪找"。references 告诉你"怎么做"。

选择条件：
- 包含多个独立子工作流
- 不同场景需要不同子集
- 全写在一个文件里太长

实际例子——`opencode-pilot`：

```markdown
# SKILL.md 写：
本 Skill 支持三种操作：
1. 创建 session → 读取 references/session-management.md
2. 发送截图 → 读取 references/media-delivery.md
3. 处理 Question → 读取 references/question-handling.md

核心约束：
- 所有操作必须先绑定路由
- 截图发送禁止使用 message 工具直发

# references/session-management.md 写：
[完整的 session 创建、绑定、切换流程——独立可执行]
```

#### 两种类型的关键区别

| 维度 | Type A（主流程型） | Type B（极简主文件型） |
|------|-------------------|---------------------|
| SKILL.md 的角色 | 完整可执行的操作手册 | 骨架 + 导航地图 |
| references 的角色 | 特定节点的补充细节 | 实际执行内容的载体 |
| 只读 SKILL.md 能否干活 | 能 | 不能，必须按导航去读 reference |
| reference 的独立性 | 低——依附于主流程某个节点 | 高——每个文件是独立子工作流 |

**产出：** 明确选择 Type A 或 Type B。

---

### Step 4）初始化目录

从零创建时，手动或用脚本创建目录结构：

```
skill-name/
├── SKILL.md
├── scripts/       （按需）
├── references/    （按需）
└── assets/        （按需）
```

只创建实际需要的子目录。如果 Skill 已存在只需迭代，跳过此步。

---

### Step 5）先写资源文件

在写 SKILL.md 之前，先把 scripts、references、assets 写好。

原因：先有内容，再写导航。否则 SKILL.md 里引用的文件不存在，或者写完 SKILL.md 后发现资源结构要改，又得回头改 SKILL.md。

操作：
1. 按 Step 2 的资源清单逐个创建
2. scripts 必须实际运行测试，确认输出正确
3. references 写完后检查：每个文件是否只覆盖一个主题
4. 只保留实际需要的目录

**产出：** 所有资源文件就绪。

---

### Step 6）写 SKILL.md

按以下固定顺序写：

#### 6a）Frontmatter

```yaml
---
name: skill-name
description: >
  这个 Skill 做什么 + 什么时候用它。
  所有触发信息都写在这里。
---
```

规则：
- `name`：小写字母 + 数字 + 连字符，64 字符以内，动词短语优先
- `description`：**这是触发机制**——AI 通过它决定是否加载此 Skill。必须同时写清"做什么"和"什么时候用"
- 不允许其他字段

**description 的好坏直接决定 Skill 能不能被正确触发。** 写得太模糊，该触发时不触发；写得太宽泛，不该触发时乱触发。

好的 description 示例：

```yaml
description: >
  调度 OpenCode 编码智能体。适用于：启动项目开发、管理 session、
  切换 agent、截图快照、转发结果。不适用于 OpenClaw 自身配置或非编码任务。
```

差的 description 示例：

```yaml
description: 一个有用的开发工具。
```

#### 6b）正文结构

正文按这个顺序组织：

1句话定位**——这个 Skill 解决什么问题
2. **固定变量**——路径、端口、环境变量等（如果有）
3. **主流程**——按顺序的操作步骤，每步包含：
   - 具体做什么（命令/操作）
   - 产出什么
   - 什么条件下需要读 reference
4. **失败处理**——常见错误和应对方式
5. **禁止事项**——绝对不能做的事
6. **References 导航**——列出所有 reference 文件及其触发条件

> 注意："触发条件"不应出现在正文中——description 已处理触发，正文只需写执行逻辑。
> 若 Skill 有多个子流程需路由，用"路由表"而非"触发条件"来组织。

#### 6c）正文写作准则

- **用祈使句**：写"运行命令"而不是"你应该运行命令"
- **给具体命令和示例**：不要只说"调用 API"，要给出实际的命令或代码片段
- **每个步骤要有产出**：读者做完这一步后应该得到什么
- **reference 引用必须带触发条件**：不是"详见 references/X.md"，而是"当遇到 Y 情况时，读取 references/X.md"

**产出：** 完整的 SKILL.md。

---

### Step 7）一致性检查（必须执行，不可跳过）

写完后逐项检查。这一步是防止"写完就交"导致的质量问题。

#### 检查 1：SKILL.md 与 references 不矛盾

逐个打开每个 reference 文件，与 SKILL.md 中涉及同一主题的段落对照：

| 检查项 | 怎么查 |
|--------|--------|
| 术语一致性 | 同一概念是否用了不同名称？ |
| 步骤顺序 | SKILL.md 说先 A 后 B，reference 是否也是？ |
| 数值/阈值 | SKILL.md 说超时 30 秒，reference 是否也是？ |
| 命令/参数 | SKILL.md 给的命令和 reference 给的是否一致？ |

发现不一致时：以 SKILL.md 为准，修改 reference。

#### 检查 2：主流程无断层

- **Type A**：只读 SKILL.md，从头到尾走一遍。每一步是否都知道做什么、怎么做、产出什么？如果某步必须读 reference 才能继续，SKILL.md 中是否明确标注了？
- **Type B**：只读 SKILL.md，是否能清楚知道每个子工作流在哪个 reference 中？导航是否完整覆盖所有场景？

#### 检查 3：References 无冗余

对每个 reference 文件问三个问题：

| 问题 | 不通过时的处理 |
|------|----------
| SKILL.md 是否链接到它并写明了触发条件？ | 没有 → 补链接，或删除该文件 |
| 内容是否与 SKILL.md 或其他 reference 重复？ | 重复 → 只保留一处，删除另一处 |
| 是否真的需要独立存在？ | 内容很少 → 合并到 SKILL.md |

#### 检查 4：无死文件

```bash
# 列出 references/ 下所有文件
ls references/

# 在 SKILL.md 中搜索每个文件名
grep "references/xxx.md" SKILL.md
```

SKILL.md 没引用的 reference 文件 = 死文件，AI 永远不会知道它存在。删除或补引用。

**产出：** 通过所有检查项，或修复后通过。

---

### Step 8）打包（可选）

需要分发时，将 Skill 目录打包为 zip（`.skill` 后缀）。打包前验证：
- frontmatter 格式和必填字段
- 命名规范和目录结构
- description 完整性
- 所有 reference 文件在 SKILL.md 中有引用

---

### Step 9）迭代

在实际使用中发现问题后：

1. 定位问题：是 SKILL.md 描述不清？reference 缺失？script 有 bug？
2. 修改对应文件
3. 重新执行 Step 7（一致性检查）
4. 测试验证

---

## SKILL.md 与 references 的关系（核心规则）

这是 Skill 编写中最容易出错的地方，单独强调。

### 规则 1：同一信息只存在于一个地方

SKILL.md 写了的内容，references 里不要再写一遍。反过来也一样。

**为什么：** 两边都写了同一件事，措辞一定会有差异。AI 读到两个版本会困惑，可能选错那个。这不是浪费 token 的问题，是直接导致执行错误。

错误示例：

```
# SKILL.md 写：
超时时间为 30 秒

# references/config.md 也写：
默认超时 60 秒
```

AI 不知道该信 30 还是 60。

正确做法：SKILL.md 写"超时时间为 30 秒"，reference 不再提超时。或者 SKILL.md 写"超时配置详见 references/config.md"，自己不写具体数值。

### 规则 2：每个 reference 必须有触发条件

不是"详见 references/X.md"，而是"当 Y 发生时，读取 references/X.md"。

没有触发条件的引用 = AI 不知道什么时候该去读 = 要么永远不读（白写），要么每次都读（浪费上下文）。

好的引用方式：

```markdown
- 若需要 OAuth2 握手细节，读取 references/api-auth.md
- 当部署到 AWS 时，读取 references/aws.md
- 遇到权限报错时，读取 references/troubleshooting.md
```

差的引用方式：

```markdown
- 更多信息见 references/api-auth.md
- 参考 references/aws.md
```

### 规则 3：references 数量最小化

目标：1-3 个。每个只覆盖一个主题。文件名一目了然。

| 好的文件名 | 差的文件名 |
|-----------|-----------|
| `api-auth.md` | `notes.md` |
| `schema.md` | `misc.md` |
| `aws-deploy.md` | `reference-1.md` |

### 规则 4：Type A 中 reference 不能接管主流程

Type A 的 reference 是"补充说明"，不是"操作步骤"。如果读者必须打开 reference 才能继续主流程的下一步，说明这部分内容应该在 SKILL.md 里。

例外：Type B 中 reference 本身就是子工作流的载体，可以包含完整操作步骤。

### 规则 5：reference 超过 100 行要加目录

```markdown
# API 认证参考

## 目录
- [OAuth2 握手](#oauth2-握手)
- [Token 刷新](#token-刷新)
- [错误码](#错误码)

## OAuth2 握手
...
```

超过 1 万字的 reference，在 SKILL.md 中提供 grep 搜索模式：

```markdown
若需查找特定错误码，在 references/api-auth.md 中搜索 `ERR-` 前缀。
```

---

## Frontmatter description 写法指南

description 是 Skill 的触发器——写得好不好直接决定 Skill 能不能在正确的时机被加载。

### 必须包含的内容

1. **这个 Skill 做什么**（一句话）
2. **具体的触发场景**（列举）
3. **不适用的场景**（如果容易混淆）

### 模板

```yaml
description: >
  [一句话说明做什么]。适用于：(1) [场景1] (2) [场景2] (3) [场景3]。
  不适用于：[容易混淆的场景]。
```

### 实际示例

```yaml
# 好——具体、有边界
description: >
  调度 OpenCode 编码智能体。适用于：启动项目开发、管理 session、
  切换 agent、截图快照、转发结果。不适用于 OpenClaw 自身配置或非编码任务。

# 好——列举了触发词
description: >
  创建或更新 AgentSkill。适用场景：(1) 从零创建新 Skill
  (2) 更新/重构已有 Skill (3) 审查 Skill 质量 (4) 打包 Skill 用于分发。
  触发词："创建 skill"、"写个 skill"、"更新 skill"。

# 差——太模糊
description: 一个有用的工具。

# 差——只说了做什么，没说什么时候用
dtion: 处理 PDF 文件。
```

---

## 常见错误速查表

| 错误 | 症状 | 修复 |
|------|------|------|
| description 太模糊 | Skill 该触发时不触发 | 补充具体触发场景和触发词 |
| "何时使用"写在正文里 | 正文触发前不加载，等于白写 | 移到 frontmatter description |
| 正文里写"触发条件"段 | 与 description 重复，浪费 Token | 删除——AI 读正文时已被触发 |
| reference 里写"入口条件/前置条件" | AI 已进入才能读到，纯冗余 | 删除——用 SKILL.md 导航控制入口 |
| reference 里写导航段 | SKILL.md 已是导航中枢，重复浪费 | 删除——导航只在 SKILL.md 维护 |
| SKILL.md 和 reference 写了同一件事 | AI 读到两个版本，可能选错 | 只保留一处，删除另一处 |
| SKILL.md 和 reference 数值矛盾 | AI 执行时用错参数 | 以 SKILL.md 为准统一 |
| reference 没有触发条件 | AI 不知道什么时候读 | 补"当 X 时，读取 references/Y.md" |
| reference 没被 SKILL.md 引用 | 死文件，AI 永远不知道它存在 | 补引用或删除 |
| Type A 中 reference 接管了主流程 | 读者必须跳转才能继续 | 把核心步骤移回 SKILL.md |
| SKILL.md 正文太长 | 上下文膨胀 | 拆为 Type B + references |
| 脚本没测试 | 运行时报错 | 实际运行并验证输出 |
| 创建了 README/CHANGELOG | 无用文件占空间 | 删除 |

---

## 禁止事项

- 禁止在 frontmatter 中添加 `name` 和 `description` 以外的字段
- 禁止 SKILL.md 和 references 写重复内容
- 禁止创建 SKILL.md 没有引用的 reference 文件
- 禁止跳过一致性检查（Step 7）
- 禁止发布未经测试的脚本
- 禁止创建 README.md、CHANGELOG.md 等辅助文件
- 禁止在 SKILL.md 正文中写"触发条件"段（description 已处理）
- 禁止在 reference 中写"入口条件/前置条件"段（AI 已进入文件才能读到）
- 禁止在 reference 中写导航段（SKILL.md 已是导航中枢，reference 不重复）
