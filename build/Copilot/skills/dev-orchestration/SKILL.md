---
name: dev-orchestration
description: "开发编排 SOP。管线控制、Agent 调度、Gate 门控、Notepad 协议、架构驱动流程。"
---

## 适用范围

企业级系统开发主协议。覆盖：Web 应用（API/数据库/前端UI）· CLI 工具 · 内部平台 · 集成服务 · 数据管线 · 自动化系统。`simple` 模式 = 轻量企业级任务管线，不限于 Web 功能迭代。

本 SKILL 由编排者（Sisyphus Enterprise 模式 / Atlas）加载。Sub-agent 不可见本文件——编排者必须将协议内容翻译为自包含委托指令。

---

## 模式与管线

| 模式 | 管线 |
|------|------|
| fullstack | P0→P1→P2→P4→P5→P6A→P6B→P7→P8 |
| fullstack+design | P0→P1→P2→P3→P4→P5→P6A→P6B→P7→P8 |
| standard | P0→P1→P2→P4→P6A→P6B→P7→P8 |
| backend | P0→P1→P2→P4→P5→P6A→P8 |
| frontend | P0→P1→P2→P4→P5→P6B→P8 |
| database | P0→P1→P2→P4→P5→P8 |
| design | P0→P1→P2→P3→P8 |
| simple | P0→P1→P2→P8 |
| review | P0→P1→P7→P8 |

## Phase 调度速查

| 阶段 | 组 | 步骤 | Agent | 并行 |
|------|----|------|-------|------|
| P0 | 1 | triage | 编排者自身 | — |
| P1 | 1 | metis-intent | @metis | — |
| P1 | 2 | explore-intel, librarian-intel | @explore, @librarian | ⚡ |
| P2 | 1 | prometheus-plan | @prometheus | — |
| P2 | 2 | momus-review, oracle-plan-review | @momus, @oracle | ⚡ |
| P3 | 1 | hephaestus-design | @hephaestus | — |
| P3 | 2 | oracle-design-review | @oracle | — |
| P3 | 3 | oracle-review-classify | 编排者自身 | — |
| P4 | 1 | conventions, doctrine, mapping | @hephaestus | ⚡ |
| P5 | 1→2→3 | contract-schema → api → types | @hephaestus | 串行 |
| P6A | 1→…→8 | B1-scaffold → … → B8-test | @hephaestus | 串行 |
| P6B | 1→…→7 | F1-scaffold → … → F7-quality | @hephaestus | 串行 |
| P7 | 1 | smoke | @hephaestus | — |
| P7 | 2 | e2e, security-validation | @hephaestus | ⚡ |
| P8 | 1 | self-verify | 编排者自身 | — |
| P8 | 2 | oracle-final | @oracle [ADVERSARIAL] | — |
| P8 | 3 | delivery | 编排者自身 | — |
| X | — | oracle-consult | @oracle | --cross |
| X | — | blocking-resolution | 视情况 | --cross |
| X | — | amendment-protocol | 视情况 | --cross |
| X | — | work-logs | 编排者自身 | --cross |

---

## 三层上下文模型

| 层 | 载体 | 内容 | 模板包含 |
|---|---|---|---|
| Agent 内建能力 | agent.md（自动加载） | 通用工程知识（N+1、TS strict、RESTful 惯例等） | 否 |
| 项目约定 | CONVENTIONS / DOCTRINE（基础清单注入） | 项目命名、错误格式、Mapper 规范、目录结构 | 否 |
| 任务特化约束 | 模板 MUST DO | 数据来源路径、产出写入路径、步骤串联规则 | **是（唯一）** |

构造 prompt 时：基础清单带入层 2，模板 MUST DO 带入层 3，层 1 不注入。

## 基础上下文注入清单

所有 @hephaestus 委托 CONTEXT 段包含以下基础项：

1. 项目技术栈与框架版本
2. `{{CONVENTIONS_PATH}}` 相关约定
3. `{{DOCTRINE_PATH}}` 相关章节
4. `{{CONTRACTS_PATH}}` 相关端点/Schema（如有）
5. Notepad Inherited Wisdom（只注入相关条目）
6. 前序步骤已创建的文件路径列表

模板标注 `[+额外注入]` 的项追加到基础之上。无标注步骤只需基础清单。

---

## 委托质量公共标准

所有 Phase 委托遵循以下公共标准。各模板如有领域特定要求则在模板内追加。

| 维度 | 标准 |
|------|------|
| 自包含 | 路径绝对路径，关键信息内联，禁止悬空引用 |
| 注入层级 | 基础清单 + CONVENTIONS + DOCTRINE + Notepad Inherited Wisdom |
| Instruction Preflight | 委托前读取 `{{INSTRUCTION_PACK_PATH}}` 并提炼注释/TODO 规范（详见下文） |
| 三层过滤 | 仅注入 Layer 3 任务特化约束。Agent 已知的通用工程知识不注入 |
| 实现类验证 | build + test + typecheck = 0 error |

### 领域特定质量追加

各模板按所属领域声明追加关注点：

| 领域 | 追加关注点 |
|------|-----------|
| 前端实现 | 用户交互体验 · 操作逻辑与点击依赖 · 展示状态完整性（loading/empty/error/success/permission-denied）· 响应式布局 |
| 后端实现 | API 联调一致性 · 接口契约比对 · 数据往返完整 · 事务与错误模型统一 |
| 方案设计 | 模块覆盖完整 · 零 TBD · 风险评估含缓解方案 · Oracle 多维审查 |
| 集成联调 | 全层验证 · Mock 残留清理 · 契约比对 · 安全验证 5 维度 |

---

## 每步操作模式

`dev-orch dispatch` 返回模板后，执行以下循环：

1. 读取 Phase 模板 → 识别下一个待完成步骤（参考"已完成步骤"与步骤概览表）
2. 收集该步骤上下文（基础清单 + 模板 `[+额外注入]`）
3. 用"任务定义"+"MUST DO"+"MUST NOT DO"构造委托 prompt
4. 发送到指定 Agent
5. SubAgent 返回后，按"完成验证"逐项检查
6. 全通过 → `dev-orch done <phase> <step>`；Phase 全步骤完成 → `dev-orch gate <phase> --auto-advance`
7. 不通过 → 按失败恢复协议处理
8. 三层过滤：Agent 已知的通用知识和 CONVENTIONS/DOCTRINE 已覆盖的约定不注入，只注入任务特化约束
9. 每步完成后执行模板末尾退出命令
10. Phase 文件含该阶段所有步骤，只处理当前步骤组，跳过已完成步骤

---

## Prompt 格式

**7-segment（实现类：@hephaestus / @explore-写入 / @librarian-深度研究）**：
PURPOSE → TASK → EXPECTED OUTCOME → MUST DO → MUST NOT DO → CONTEXT → QUALITY

**3-segment（研究类：@explore / @librarian / @metis / @oracle）**：
CONTEXT → GOAL → REQUEST

质量自检：自包含？有路径？有 MUST DO/NOT？可验证？实现类 prompt ≥ 30 行。

---

## Instruction Preflight

发布实现类委托前（@hephaestus / @explore-写入 / @librarian-深度研究），必须在 prompt MUST DO 注入预制段：

1. 读取 `{{INSTRUCTION_PACK_PATH}}`，禁止只贴路径不阅读
2. 提炼 3-5 条与当前任务最相关的规范，写入本次 prompt
3. 至少覆盖：注释规范 + TODO/FIXME 标签规范
4. 要求 SubAgent 汇报中回传"已遵循规则清单 + 标签位置（文件:行号）"

未注入预制段不得发布实现类委托。

---

## Gate 二审协议

每个 Gate 标记 `passed` 前，必须先完成一次咨询/审查（@oracle 或 @momus），证据落盘。

证据格式遵循 `{{GATE_REVIEW_SPEC_PATH}}`。最低字段（缺一不可）：

- Gate: `<phase>/<gate>`
- Reviewer
- Scope
- Upstream-Dependencies
- Downstream-Dependencies
- Verdict: PASS

执行要求：
1. 证据写入 `.sisyphus/reviews/<phase>-<gate>.md`
2. `dev-orch mark <phase> <gate> passed` 的 reason 必须传证据路径
3. Gate 校验会二次读取证据文件，防止绕过

---

## CLI 命令

| 命令 | 用途 |
|------|------|
| `dev-orch init <mode> <task-name>` | 初始化项目 |
| `dev-orch route [--verbose]` | 获取当前路由 |
| `dev-orch dispatch <phase>` | 获取 Phase 完整指令 |
| `dev-orch dispatch --cross <template>` | 横切 dispatch |
| `dev-orch gate <phase>` | 检查门控 |
| `dev-orch gate <phase> --auto-advance` | 检查门控 + 自动推进 |
| `dev-orch mark <phase> <gate> passed "<review-path>"` | 标记门控通过 |
| `dev-orch mark <phase> <gate> skipped "<reason>"` | 跳过门控 |
| `dev-orch done <phase> <step> [step2 ...]` | 标记步骤完成 |
| `dev-orch redo <phase> <step> [step2 ...] [--force]` | 重置步骤 |
| `dev-orch advance` | 推进阶段 |
| `dev-orch current` | 查看当前状态 |

---

## 用户交互边界

默认自动继续。仅以下三类场景允许 ask_user：
1. 需求存在多种合理解释，且显著影响范围/方案/交付边界
2. 外部阻塞成立，自动手段已穷尽
3. 缺少只有用户能提供的业务决定、权限、账号或环境信息

"是否继续""是否批准"等流程审批问题不得打断用户。

## 外部研究边界

编排者不得直接加载 ask-others SKILL。需外部研究升级时：编排者 → @librarian → ask-others。

---

## 架构先行判定

| 决策空间 \ 技术栈 | 固定 | 半固定 | 未定 |
|---|---|---|---|
| 低 | L0: 直接实现 | L1: 轻量备忘 | L1: 锁定最小边界 |
| 中 | L1/L2: 模块蓝图 | L2: 关键接口 | L2/L3: 选型收敛 |
| 高 | L2: 系统重组 | L3: 架构+权衡 | L3: 完整架构 |

L0/L1：编排者自行处理。L2/L3：委托 @prometheus。L3 产出强制经 @oracle 审查。

---

## Notepad 协议与状态目录

### Notepad

```
.sisyphus/notepads/{plan-name}/
  project-context.md   # 项目全貌
  learnings.md         # 约定和陷阱
  decisions.md         # 架构决策
  issues.md            # 问题追踪
  problems.md          # 未解决阻塞
  checkpoint.md        # 断点快照
```

- append-only（project-context.md 和 checkpoint.md 可整段更新）
- 委托前必读 → 提取 Inherited Wisdom → 注入 CONTEXT 段（只注入相关条目）
- 一条=一行、含路径/行号、零口水话

### 目录职责边界

| 目录 | 职责 | 不承载 |
|------|------|--------|
| `.sisyphus/notepads/` | 编排共享工作记忆（上下文/决策/问题/阻塞/断点） | Gate 证据、Phase 日志 |
| `.sisyphus/reviews/` | Gate 二审、对抗审查、复核证据 | 过程性工作日志 |
| `{{LOG_DIR}}/` | 运营性 work-log（决策/情报/审查轮次/阻塞跟踪） | Notepad 共享记忆 |
| `dev-orch dispatch` 输出 | 瞬时执行指令 | 持久化状态源 |

执行结论必须回写到 notepad/reviews/work-logs/CLI state，不回写 dispatch 输出。

---

## 迭代协议

- `dev-orch redo <phase> <step>`：重置步骤 + 门控 + 迭代计数器+1
- Round 3 警告、Round 5 拒绝（除非 --force）
- 审查不通过 → redo 前置步骤，不 redo 审查步骤本身
- 失败恢复：1次→修根因；2次→换方案+@oracle；3次→停止+回滚+@librarian 查案例

## 上下文溢出预防

- 精简注入：notepad → 只提取相关条目
- Agent 结果综合：保留路径/行号/决策，不复述原文
- 溢出时：写 checkpoint.md → 更新 Todo → `dev-orch current` → 断点续做
- 新对话恢复：`dev-orch route --verbose` + 读 notepad

---

## 读取禁区

- `scripts/` 源码：通过 CLI 交互，不读源码
- `data/templates/*.md`：通过 `dev-orch dispatch` 获取渲染结果，不直接读模板
