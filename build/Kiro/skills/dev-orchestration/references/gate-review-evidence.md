# Gate 二审证据文件规范

## 1. 目的与适用范围

- 适用于所有 `dev-orch mark <phase> <gate> passed "<review-path>"`。
- 执行 `mark ... passed` 前必须先生成并通过本规范校验。
- 缺字段、空字段、泛化描述视为无效证据。

## 2. 必填字段

按以下顺序填写，字段名必须完全一致：

1. Gate
2. Reviewer
3. Scope
4. Upstream-Dependencies
5. Downstream-Dependencies
6. Verdict: PASS

## 3. 字段定义

- Gate: 使用 `<phase>/<gate>`，示例 `P8/self_verify_pass`。
- Reviewer: 写明执行审查的角色或 Agent，示例 `@oracle`、`@momus`。
- Scope: 列出本次判定覆盖的文件与行为边界；至少 2 项。
- Upstream-Dependencies: 列出上游输入来源与影响点；至少 1 项。
- Downstream-Dependencies: 列出下游消费方与潜在影响；至少 1 项。
- Verdict: 固定写 `PASS`，不得写其他值。

## 4. 填写要求

- 使用 Markdown 列表或表格，不得混用不完整格式。
- 依赖项最小粒度到模块/文件级；必要时补充接口或命令。
- 每条依赖影响必须包含“对象 + 影响 + 结论”。
- 禁止空泛语句：
  - 禁止 `已检查无问题`。
  - 禁止 `影响很小`。
  - 禁止 `基本正常`。
- Scope 禁止写成 `全量`、`全部`、`相关代码` 等泛词。
- Reviewer 禁止留空、禁止写 `团队`、`多人`。
- Gate 与文件名中的 `<phase>-<gate>` 必须一致。

## 5. 文件命名约定

- 路径固定：`.sisyphus/reviews/<phase>-<gate>.md`。
- `<phase>` 使用大写阶段号，示例 `P8`。
- `<gate>` 使用 gate 标识原文，不做语义改写。
- 一个 gate 一份文件，不得复用同一文件覆盖多个 gate。

## 6. 标准示例（可复制）

```markdown
# Gate Review Evidence
- Gate: P8/self_verify_pass
- Reviewer: @oracle
- Scope:
  - dev-orchestration/data/templates/P8.md: self-verify 流程与 gate 咨询动作
  - dev-orchestration/SKILL.md: Gate 二审协议与证据引用规则
- Upstream-Dependencies:
  - .sisyphus/plans/<task>.md: self-verify 检查项来源已覆盖，结论为一致
  - dev-orch dispatch --cross oracle-consult: 咨询输入包含当前变更范围，结论为充分
- Downstream-Dependencies:
  - dev-orch mark P8 self_verify_pass passed "...": 依赖证据文件字段完整，结论为可执行
  - .sisyphus/reviews/P8-self_verify_pass.md: 被 gate 复核读取，结论为可追溯
- Verdict: PASS
```

## 7. 错误示例（不合格）

Gate 格式错误（缺 `<phase>/<gate>`）· Reviewer 非明确角色 · Scope 空泛 · 依赖未含对象与影响 · Verdict 非 `PASS` — 均为不合格。