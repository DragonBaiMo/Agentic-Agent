---
name: 接口契约
description: RESTful API 接口设计规范。覆盖统一响应结构、HTTP 状态码、分页、幂等、版本策略、错误格式。适用于任意后端接口层（HTTP/REST）。通用规范见 code-quality.instructions.md。
applyTo: "**/*.ts, **/*.tsx, **/*.js, **/*.jsx, **/*.py, **/*.java, **/*.kt, **/*.go, **/*.rs"
---

# 接口契约规范

## 统一响应结构

所有接口响应必须使用统一 JSON 包装，禁止裸字符串或裸数据返回：

```json
{ "code": 0, "data": { ... }, "message": "操作成功" }
{ "code": 40001, "error": "VALIDATION_ERROR", "message": "用户名不能为空", "details": [...] }
```

- `code`：业务状态码，`0` 表示成功，非零表示具体错误类型
- `data`：成功时的载荷，失败时省略或为 `null`
- `message`：人可读说明
- `error`：错误类型枚举标识（失败时必填）
- `details`：校验失败等场景的字段级错误数组（可选）

## HTTP 状态码

| 码 | 语义 | 场景 |
|----|------|------|
| 200 | 成功 | GET / PUT / PATCH |
| 201 | 已创建 | POST |
| 204 | 无内容 | DELETE |
| 400 | 请求错误 | 参数校验失败 |
| 401 | 未认证 | 缺少 / 无效 token |
| 403 | 无权限 | 认证通过但无权 |
| 404 | 不存在 | 资源未找到 |
| 422 | 无法处理 | 业务校验失败 |
| 429 | 过多请求 | 限流 |
| 500 | 服务器错误 | 未捕获异常 |

HTTP 状态码与业务 `code` 字段双重表达；两者语义必须一致，不得状态码 200 但业务 `code` 表示失败。

## 路由设计

- 资源用复数名词：`/users`、`/orders`、`/products`
- 操作用 HTTP 动词，禁止在路径中写动词（`/getUser`、`/createOrder`）
- 嵌套资源最多两层：`/users/{id}/orders`，更深层改用查询参数
- 路径全小写 kebab-case：`/order-items`

```
GET    /users          # 列表
POST   /users          # 创建
GET    /users/{id}     # 详情
PUT    /users/{id}     # 全量更新
PATCH  /users/{id}     # 局部更新
DELETE /users/{id}     # 删除
```

## 幂等性

- `GET` / `PUT` / `DELETE` 必须幂等
- `POST` 支持 `Idempotency-Key` 请求头，相同 key 重复调用返回首次结果，不重复执行副作用

```http
POST /payments
Idempotency-Key: uuid-v4-from-client
```

## 分页

统一使用以下参数格式，禁止自创分页参数名：

```
GET /resource?page=1&size=20&sort=field:desc
```

响应中必须包含分页元数据：

```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "size": 20
  }
}
```

## 版本策略

- 优先使用 URL 路径版本：`/v1/users`
- 破坏性变更必须升版本（`v1` → `v2`），不得在同版本内修改字段语义或删除字段
- 旧版本保留至少一个大版本生命周期，需有 `Deprecation` 响应头提示

```http
Deprecation: true
Sunset: Sat, 31 Dec 2026 00:00:00 GMT
```

## 错误格式

错误响应结构必须统一，禁止在不同接口返回不同错误格式：

```json
{
  "code": 40001,
  "error": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "details": [
    { "field": "email", "message": "邮箱格式不正确" },
    { "field": "age",   "message": "年龄必须大于 0" }
  ]
}
```

业务错误码用带语义的枚举常量管理，禁止魔法数字散落代码中。

## 契约要求

每个接口文档（OpenAPI/代码注释）必须包含：

- 所有字段的类型约束与是否必填
- 完整的错误码列表及触发条件
- 请求与响应的示例 payload
- 认证方式声明（Bearer / API Key / 无）

## 禁止模式

| 禁止 | 替代 |
|------|------|
| 响应裸字符串 / 裸数组 | 统一 `{ code, data, message }` 包装 |
| 路径中含动词（`/getUser`） | HTTP 动词 + 名词路径 |
| 状态码 200 但业务层表示失败 | HTTP 状态码与业务 code 语义一致 |
| 无 `Idempotency-Key` 的 POST 副作用接口 | 接入幂等键机制 |
| 同版本内删除或改变字段语义 | 升版本 + 旧版本保留期 |
| 自定义分页参数名 | 统一 `page` / `size` / `sort` |
| 业务错误码魔法数字 | 枚举常量 + 集中管理 |
