# Phase 6A: 后端实现

## 步骤概览

| 步骤 | Agent | 组 | 并行 |
|------|-------|---|------|
| B1-scaffold | @hephaestus | g1 | 串行 |
| B2-migration | @hephaestus | g2 | 串行 |
| B3-data-access | @hephaestus | g3 | 串行 |
| B4-feature | @hephaestus | g4 | 串行 |
| B5-middleware | @hephaestus | g5 | 串行 |
| B6-security | @hephaestus | g6 | 串行 |
| B7-observability | @hephaestus | g7 | 串行 |
| B8-test | @hephaestus | g8 | 串行 |

已完成步骤: {{COMPLETED_STEPS}}

## 委托质量标准

> 委托质量标准请务必遵循主 SKILL 协议。

P6A 追加（后端实现）：API 联调一致性 · 接口契约比对 · 数据往返完整 · 事务与错误模型统一 · build + test + typecheck = 0 error。

---

## 企业级派发强化提醒（编排者 → @hephaestus）

- 发布企业级开发任务时，编排者必须在 7-segment MUST DO 中额外强调以下实现细节：DTO 类型安全、参数校验、事务管理、异常处理、错误码枚举、日志增强、SSRF 防护、Entity 隔离。
- 涉及 SQL 的实现必须优先采用标准化 SQL（ANSI SQL）；如必须使用方言语法，需在 {{CONVENTIONS_PATH}} 记录使用理由、兼容性影响和回退方案。

---

## Step: B1-scaffold
> @hephaestus — 创建后端项目骨架，从零到可启动

**注入上下文** 基础清单

**MUST DO**
- 框架/目录结构/包管理器选型决策记录到 {{CONVENTIONS_PATH}}
- 缺少必要 env var → 进程立即退出，不静默用默认值
- 目录结构遵循 {{DOCTRINE_PATH}} B.1（按业务模块组织，禁止按纯技术层平铺）

**完成验证**
- [ ] `GET /health` → 200
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B1 → completed

**退出**: `dev-orch done P6A B1-scaffold`

---

## Step: B2-migration
> @hephaestus — 将契约/计划中的数据模型落地为数据库表结构

**注入上下文** 基础清单 + {{CONTRACTS_PATH}} 数据模型定义（如无契约，使用 P2 计划中的数据模型）

**MUST DO**
- Schema 来源 = 契约或计划文档（不凭记忆建表）
- 迁移工具选型记录到 {{CONVENTIONS_PATH}}
- dry-run → 检查 → 执行 up → 验证 → 测试 down 回滚（分步，不一步到位）
- 每个 migration 包含 up + down（可回滚），不可逆操作需 @oracle 审查

**完成验证**
- [ ] `migration up` 成功，表结构与契约一致；`migration down` 回滚成功
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B2 → completed

**退出**: `dev-orch done P6A B2-migration`

---

## Step: B3-data-access
> @hephaestus — 实现 Repository 层 CRUD 封装，为业务层提供数据访问接口

**注入上下文** 基础清单 + B2 产出的数据库 Schema

**MUST DO**
- ORM/查询库选型记录到 {{CONVENTIONS_PATH}}
- 原生 SQL 查询必须使用标准化 SQL（ANSI SQL）并参数化；方言特性仅在必要时使用且需在 {{CONVENTIONS_PATH}} 留痕
- 禁止直接返回 ORM Entity — 必须经 Mapper 转为 Response DTO（遵循 {{DOCTRINE_PATH}} B.2）

**完成验证**
- [ ] 每实体 CRUD 方法完整，多表写入有事务保护
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B3 → completed

**退出**: `dev-orch done P6A B3-data-access`

---

## Step: B4-feature
> @hephaestus — 按 Feature Slice 实现业务模块全部端点

**注入上下文** 基础清单 + 业务-工程映射表

**MUST DO**
- 业务-工程映射表决定子迭代拆分（模块 ≥3 时按模块分批实施，编排者在 notepad 追踪各批次进度）
- 每端点覆盖 5 类场景：success / validation / conflict / not-found / permission
- 首个子迭代完成后验证 DOCTRINE 范式符合度，偏差记录到 {{CONVENTIONS_PATH}}
- 每个 handler 写之前先定义：DTO / 错误枚举 / 数据访问路径（Pre-Flight）
- DTO 强类型定义必须先于业务实现，入口参数必须全量校验
- 错误码使用枚举集中管理，禁止在 handler/service 中散落硬编码错误码
- 遵循 {{DOCTRINE_PATH}} B.2 请求处理流：Handler → Input DTO → Service → Repository → Mapper → Response DTO
- 遵循 {{DOCTRINE_PATH}} B.3 错误模型：统一 AppError + 全局 error handler
- 提供 Seed Data 脚本（开发/测试用初始数据），覆盖正常 + 边界 + 空状态

**完成验证**
- [ ] 路由路径与契约完全一致（路径 + 方法 + 参数 + 响应）
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B4（或 B4.x）→ completed

**退出**: `dev-orch done P6A B4-feature`

---

## Step: B5-middleware
> @hephaestus — 实现中间件链：认证、授权、校验、错误处理

**注入上下文** 基础清单 + B4 端点清单

**MUST DO**
- 中间件执行顺序显式声明并记录到 {{CONVENTIONS_PATH}}
- 禁止裸 throw Error — 必须使用类型化 AppError（遵循 {{DOCTRINE_PATH}} B.3）
- 所有入口 Schema 校验（zod / class-validator / joi 等）
- 统一错误码枚举与异常映射策略（异常类型 → 错误码 → HTTP 状态）并记录到 {{CONVENTIONS_PATH}}

**完成验证**
- [ ] 401/403 区分正确，错误响应格式统一
- [ ] 无效输入返回校验错误，格式符合统一错误模型
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B5 → completed

**退出**: `dev-orch done P6A B5-middleware`

---

## Step: B6-security
> @hephaestus — 安全加固：密钥管理、限流、依赖审计

**注入上下文** 基础清单 + 安全要求文档（如无，按 OWASP Top 10 基线）

**MUST DO**
- `grep -r` 验证源码零硬编码密钥
- `npm audit` / `bun audit` 无 critical 漏洞
- 禁止直接序列化 DB Entity 返回前端 — 必须经 Mapper + ResponseDTO（遵循 {{DOCTRINE_PATH}} B.2）
- 公开端点有限流保护
- 涉及外部 URL/回调/抓取能力时必须实现 SSRF 防护（协议白名单、内网网段阻断、重定向与 DNS Rebinding 防护）

**完成验证**
- [ ] grep 清洁 + audit 通过
- [ ] 响应无内部字段泄露
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B6 → completed

**退出**: `dev-orch done P6A B6-security`

---

## Step: B7-observability
> @hephaestus — 可观测性基础设施：日志、健康检查增强

**注入上下文** 基础清单 + B5 请求日志中间件实现

**MUST DO**
- 健康检查 `/health` 包含 DB 连通性验证
- 日志框架选型记录到 {{CONVENTIONS_PATH}}
- 日志为结构化格式（可机器解析），禁止 console.log 式纯字符串日志

**完成验证**
- [ ] `GET /health` → 200，响应含 DB 状态
- [ ] 日志输出为结构化格式
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B7 → completed

**退出**: `dev-orch done P6A B7-observability`

---

## Step: B8-test
> @hephaestus — 补全三层测试：单元 + 集成 + E2E

**注入上下文** 基础清单 + B4 端点验证检查清单


**测试方法论参考** 执行前读取以下文件获取完整测试规范：
- 单元测试：`c:\Users\Dragon\.copilot\skills\ai-testing-workflow\references\unit-testing.md`
- 集成测试：`c:\Users\Dragon\.copilot\skills\ai-testing-workflow\references\integration-testing.md`
- 可测试性重构：`c:\Users\Dragon\.copilot\skills\ai-testing-workflow\references\testability-refactor.md`
**MUST DO**
- 测试框架全项目统一
- 覆盖率：行 ≥80%，分支 ≥60%
- 连续运行 3 次全绿
- Integration 测试连接真实 DB（或 in-memory 替代），不 mock 数据层
- 遵循 {{DOCTRINE_PATH}} B.4 测试矩阵：success / validation / business-rule / conflict / not-found / permission

**完成验证**
- [ ] 全部测试通过，覆盖率达标，3 次全绿
- [ ] `{{SYNC_DIR}}/backend-progress.md`：B8 → completed

**退出**: `dev-orch done P6A B8-test`

---

## 退出 Gate

## Gate 二审（必做）

- 先执行 `dev-orch dispatch --cross oracle-consult` 做架构与依赖影响复核。
- 生成 `{{REVIEW_DIR}}/P6A-<gate>.md`，必须包含 Upstream/Downstream 依赖影响。
- 完成证据文件后再执行 `dev-orch mark P6A <gate> passed "<review-path>"`。

全部通过才能进入 P7：
- [ ] 每个模块 service 不直接导入其他模块的 repository（模块边界）
- [ ] 所有响应经 Response DTO，无 Entity 泄露
- [ ] 写操作有事务，事务范围不超出单个 service 方法
- [ ] 全局 error handler + 类型化 AppError，无裸 throw
- [ ] 每个 Feature Slice 满足 {{DOCTRINE_PATH}} B.4 测试矩阵
- [ ] {{SYNC_DIR}}/backend-progress.md 全部步骤 → completed


