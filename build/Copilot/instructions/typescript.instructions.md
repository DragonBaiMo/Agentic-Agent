---
name: TypeScript 代码质量
description: TypeScript / JavaScript 专属编码规范。覆盖模块结构、类型安全、导入规则、禁止模式。通用规范见 code-quality.instructions.md。
applyTo: "**/*.ts, **/*.tsx, **/*.js, **/*.jsx, **/*.vue, **/*.svelte"
---

# TypeScript / JavaScript 编码规范

## 文件命名

- 文件 / 目录统一 kebab-case：`my-module.ts`、`tool-registry.ts`
- 模块入口文件只能是 `index.ts`，仅做 barrel export，禁止写业务逻辑

## 模块结构

- 跨模块导入必须通过对应模块的 `index.ts` barrel 入口

```typescript
// ✓ 正确
import { log } from "./shared"

// ❌ 禁止 — 不直接引用模块内部文件
import { log } from "./shared/log"
```

- 禁止路径别名（如 `@/`），仅允许相对路径
- 禁止默认导出，统一具名导出

## 类型安全

- 所有函数参数与返回值类型显式标注
- 系统边界用 `unknown` + 类型守卫逐步收窄，绝不用 `any`：

```typescript
// ✓ 正确
function parse(input: unknown): Config {
  if (!isValidConfig(input)) throw new Error("Invalid config")
  return input
}

// ❌ 禁止
function parse(input: any): Config {
  return input as Config
}
```

- 运行时校验用 Zod（v4）或等价 Schema 库
- 工厂函数优于带构造函数的 class

## 禁止模式

| 禁止 | 替代 |
|------|------|
| `as any` | 类型收窄 / `unknown` + 类型守卫 |
| `@ts-ignore` / `@ts-expect-error` | 修复类型错误本身 |
| `export default` | 具名导出 `export { name }` |
| 在 `index.ts` 写业务逻辑 | 抽离到具名文件，`index.ts` 仅 barrel |
| 路径别名 `@/` | 相对路径 `./` / `../` |

## 错误处理

```typescript
// ✓ 正确 — 携带上下文
catch (error) {
  log.error("Failed to process order", { orderId, userId, error })
  throw error
}

// ❌ 禁止 — 空 catch / 无上下文
catch (e) {}
catch (e) { console.log(e) }
```

## 常见根因速查

遇类型 / 构建错误按序排查：

1. barrel `index.ts` 缺少导出
2. Zod schema 与推断类型（`z.infer`）不匹配
3. 类型定义库版本冲突（如 `bun-types` vs `@types/node`）
4. 循环依赖导致的 `undefined` 类型
