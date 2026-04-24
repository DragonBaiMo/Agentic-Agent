---
name: SQL 代码质量
description: SQL 专属编码规范。强制使用 ANSI/ISO 标准 SQL，禁止数据库方言特有语法。覆盖标准化语法替代、格式、命名、JOIN、安全。通用规范见 code-quality.instructions.md。
applyTo: "**/*.sql"
---

# SQL 编码规范

**核心约束**：使用 ANSI/ISO 标准 SQL，禁止数据库方言特有语法。确需方言时显式隔离并声明。

---

## 文件管理

- **单一演化源**：项目保留的 `.sql` 文件必须是持续演化的单一真相源（`schema.sql` / `seed.sql` 等），持续更新而非堆积
- **禁止一次性 .sql 文件**：临时执行 SQL（数据修正、调试查询、一次性迁移）不得创建独立 `.sql` 文件后遗留不管
- **临时执行路径**：临时 SQL 通过脚本 / CLI 直接执行；必须落盘时放项目 `tmp/`（见 `code-quality.instructions.md` 临时产物规范）
- **例外**：迁移工具（Flyway / Liquibase / Alembic / Prisma Migrate 等）产生的版本化迁移文件，遵循工具自身规范
- **清理**：执行已完成、不再作为真相源的独立 SQL 文件必须删除，不留废弃文件

---

## 标准化替代表

| 场景 | 禁止（方言） | 标准替代 |
|------|-------------|---------|
| 分页 | `LIMIT n OFFSET m`（MySQL/PG）· `TOP n`（SQL Server）· `ROWNUM`（Oracle） | `OFFSET m ROWS FETCH NEXT n ROWS ONLY` |
| NULL 合并 | `IFNULL`（MySQL）· `NVL`（Oracle）· `ISNULL`（SQL Server） | `COALESCE(a, b, ...)` |
| 字符串拼接 | `+`（SQL Server）· `CONCAT_WS`（MySQL 专有） | `a \|\| b` 或 `CONCAT(a, b)` |
| 类型转换 | `::type`（PG）· `CONVERT(type, x)`（SQL Server） | `CAST(x AS type)` |
| 当前时间戳 | `GETDATE()`（SQL Server）· `NOW()`（MySQL/PG） | `CURRENT_TIMESTAMP` |
| 当前日期 | `CURDATE()`（MySQL）· `SYSDATE`（Oracle） | `CURRENT_DATE` |
| 布尔 | `1/0` + `TINYINT`（MySQL） | `TRUE` / `FALSE` + `BOOLEAN` |
| 标识符引号 | 反引号 `` ` `` · 方括号 `[]` | 双引号 `"column"` |
| 自增列 | `AUTO_INCREMENT`（MySQL）· `IDENTITY`（SQL Server） | `GENERATED ALWAYS AS IDENTITY` |
| Upsert | `ON DUPLICATE KEY UPDATE` · `REPLACE INTO` | `MERGE INTO ... WHEN MATCHED` |
| 返回插入行 | `RETURNING`（PG）· `OUTPUT`（SQL Server） | 拆为 `INSERT` + `SELECT`（如必要） |
| 条件表达 | `IIF(c, a, b)`（SQL Server）· `IF(c, a, b)`（MySQL） | `CASE WHEN c THEN a ELSE b END` |
| 虚表 | `FROM DUAL`（Oracle） | 省略（标准 SQL 不需要） |

---

## 方言隔离（例外路径）

必须用方言时（性能 / 标准 SQL 无等价 / 已有生态绑定）：

1. 文件头部显式声明目标数据库与原因：

```sql
-- DIALECT: postgresql@>=12
-- REASON: 批量 UPSERT 性能要求，MERGE 在 PG14 前不可用
-- STANDARD_EQUIV: 无
INSERT INTO users (id, name) VALUES (?, ?)
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
```

2. 方言文件独立目录（如 `migrations/postgres/`），不与标准 SQL 混放
3. 应用层提供抽象（ORM / QueryBuilder），方言 SQL 仅出现在迁移 / 存储过程 / 索引优化脚本

---

## 格式与命名

- 关键字全大写：`SELECT` / `FROM` / `WHERE` / `JOIN` / `GROUP BY`
- 标识符全小写 snake_case：`user_id`、`order_items`
- 表名风格全局一致（全复数或全单数，不混用）
- 每个主要子句独占一行：

```sql
-- ✓ 正确
SELECT u.id, u.name, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active'
GROUP BY u.id, u.name
ORDER BY order_count DESC
OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY;
```

---

## 查询规则

- 禁止 `SELECT *`：必须显式列出列名
- JOIN 必须显式指定类型（`INNER JOIN` / `LEFT JOIN` / `RIGHT JOIN` / `FULL JOIN`）
- 禁止逗号分隔的隐式 JOIN：`FROM a, b WHERE a.id = b.a_id` → `FROM a INNER JOIN b ON b.a_id = a.id`
- `GROUP BY` 列与 `SELECT` 非聚合列严格一致
- `ORDER BY` 用列名或表达式，不用序号（`ORDER BY 1` 禁止）

---

## 安全

- 参数化查询：禁止字符串拼接 SQL 传入用户输入
- 禁止 `WHERE 1=1` 动态拼接；用 QueryBuilder 或预定义谓词集
- 权限最小化：应用账号仅授予所需 DML；DDL / 管理操作独立账号
- 敏感列（密码哈希 / token / 身份证）禁止明文日志与错误回显

---

## DDL

- 所有表必须有主键
- 外键显式声明并命名（`fk_<table>_<col>`）
- 索引命名：`idx_<table>_<col>[_<col>]`
- 字段类型优先标准类型（`VARCHAR`、`INTEGER`、`DECIMAL(p,s)`、`TIMESTAMP`、`BOOLEAN`）
- 时间列统一用带时区（`TIMESTAMP WITH TIME ZONE`）或明确约定 UTC
- 迁移脚本必须可回滚（配对 `up` / `down`）

---

## 禁止模式

| 禁止 | 原因 / 替代 |
|------|----------|
| `SELECT *` | 显式列出列名 |
| 隐式 JOIN（逗号） | `INNER JOIN ... ON ...` |
| 字符串拼接 SQL | 参数化查询 |
| `WHERE 1=1` 动态拼接 | QueryBuilder / 谓词集 |
| 方言函数未隔离 | 迁移到标准替代或放入方言文件 |
| `ORDER BY 1` / 序号 | 列名或表达式 |
| 存储过程写业务逻辑 | 业务逻辑上移应用层 |
| 触发器做审计 / 校验 | 应用层或事件流 |
| 大事务跨业务步骤 | 拆为小事务 + 补偿 |
