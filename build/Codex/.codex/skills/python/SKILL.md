---
name: python
description: "Python 专属编码规范。覆盖命名、类型标注、异常处理、包结构。通用规范见 code-quality.instructions.md。 Use when editing files matching: **/*.py"
---

# Python 编码规范

## 命名

- 文件 / 目录：snake_case（`order_service.py`、`data_loader.py`）
- 类名 PascalCase，函数 / 变量 snake_case，常量 UPPER_SNAKE_CASE
- 包入口 `__init__.py` 仅做导出
- 禁止笼统文件名：`utils.py`、`helpers.py`、`common.py`

## 类型标注

- 所有公共函数参数和返回值必须有 type hints（PEP 484）

```python
# ✓ 正确
def calculate_total(items: list[OrderItem], discount: float = 0.0) -> Decimal:
    ...

# ❌ 禁止 — 无类型标注
def calculate_total(items, discount=0.0):
    ...
```

- 系统边界输入用 Pydantic model 做运行时校验
- 复杂类型用 `TypeAlias` / `TypeVar` 保持可读性

## 异常处理

```python
# ✓ 正确 — 捕获具体异常，携带上下文，保留链
except FileNotFoundError as e:
    logger.error("配置文件不存在: %s", config_path, exc_info=True)
    raise ConfigError(f"无法加载 {config_path}") from e

# ❌ 禁止 — 裸 except / 吞异常
except:
    pass
except Exception:
    pass
```

- 资源管理用 `with`（context manager）
- 异常链用 `raise ... from e`

## 包结构

```
src/
├── __init__.py
├── config.py           # 配置
├── models/             # 数据模型 / Pydantic schema
├── services/           # 业务逻辑
├── repositories/       # 数据访问
└── exceptions.py       # 自定义异常
```

## 禁止模式

| 禁止 | 替代 |
|------|------|
| 裸 `except:` / `except Exception: pass` | 捕获具体异常，记录或重抛 |
| 无 type hints 的公共函数 | 完整类型标注 |
| 可变默认参数 `def f(x=[])` | `def f(x: list \| None = None)` |
| `from module import *` | 显式导入具名符号 |
| 全局可变状态 | 依赖注入或函数参数传递 |
| `os.system()` / 字符串拼接 subprocess | `subprocess.run([...], check=True)` 列表形式 |
