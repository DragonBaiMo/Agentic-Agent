---
name: Java 代码质量
description: Java / Kotlin 专属编码规范。覆盖命名、类型安全、异常处理、包结构。通用规范见 code-quality.instructions.md。
applyTo: "**/*.java, **/*.kt"
---

# Java / Kotlin 编码规范

## 命名

- 文件名 = 类名，PascalCase（`OrderService.java`）
- 包名全小写，按功能域组织（`com.example.order.service`）
- 常量 UPPER_SNAKE_CASE，变量 / 方法 camelCase
- 禁止笼统包名：`util`、`helper`、`common`、`misc`

## 类型安全

- 禁止 raw type：`List<String>` 不写 `List`
- 可能为空的返回值用 `Optional<T>`，禁止返回 null 让调用方猜
- 泛型边界明确：`<T extends Comparable<T>>`
- 强制转型前必须 `instanceof` 检查

## 异常处理

```java
// ✓ 正确 — 捕获具体异常，携带上下文
catch (IOException e) {
    log.error("读取配置文件失败: {}", configPath, e);
    throw new ConfigLoadException("无法加载 " + configPath, e);
}

// ❌ 禁止 — 吞异常 / 仅打印
catch (Exception e) {}
catch (Exception e) { e.printStackTrace(); }
```

- 可恢复错误用 checked exception，编程错误用 unchecked
- 禁止用异常做流程控制
- 资源释放用 try-with-resources 或 finally

## 包结构

```
src/main/java/com/example/project/
├── config/          # 配置类
├── controller/      # 入口层（参数校验 / 路由）
├── service/         # 业务逻辑
├── repository/      # 数据访问
├── model/           # 领域对象 / DTO
└── exception/       # 自定义异常
```

- 跨包访问通过公共接口，禁止直接引用内部实现类
- 包内类尽量 package-private，只有 API 表面用 `public`

## 依赖注入

- 构造函数注入；禁止字段注入 `@Autowired`
- 依赖接口而非具体实现

## 禁止模式

| 禁止 | 替代 |
|------|------|
| raw type `List` | `List<String>` |
| 返回 null | `Optional<T>` |
| `e.printStackTrace()` | 结构化日志 `log.error(...)` |
| 字段注入 `@Autowired` | 构造函数注入 |
| 异常做流程控制 | 条件判断 |
