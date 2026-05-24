# Phase 1 — 单元测试

针对单个方法/函数的测试。目标：验证每个函数在各种输入条件下的行为正确性。

---

## 1.1 测试四要素（每个用例必须包含）

| 要素 | 含义 | 示例 |
|------|------|------|
| **测试数据** | 输入值、边界值、异常值 | `user_id="valid-123"`, `user_id=""`, `user_id=None` |
| **前置条件** | 测试执行前系统必须处于的状态 | 数据库已有该用户记录 / Mock 返回预设值 |
| **测试步骤** | 调用目标方法的具体操作序列 | `result = service.get_user("valid-123")` |
| **预期输出** | 方法应该返回什么 / 产生什么副作用 | `assert result.name == "张三"` / `assert mock_db.save.called` |

**AI 提示词模板**（给 AI 下达测试任务时使用）：

```
对 {模块/文件} 中的所有公共方法编写单元测试：
- 覆盖率目标：不低于 70%
- 每个测试用例包含：测试数据 + 前置条件 + 测试步骤 + 预期输出
- 使用白盒测试方法，覆盖主路径 + 分支路径 + 边界条件
- 依赖项使用 Mock/Stub 替代
- 遵循 Arrange-Act-Assert 模式
```

---

## 1.2 白盒测试方法

单元测试使用白盒方法——基于代码内部结构设计用例。

### 逻辑覆盖（按覆盖强度递增）

| 覆盖级别 | 含义 | 最低要求 |
|----------|------|----------|
| 语句覆盖 | 每条语句至少执行一次 | ⚠️ 太弱，不推荐作唯一标准 |
| 判定覆盖 | 每个 if/switch 的 True + False 分支都走过 | ✅ 基本要求 |
| 条件覆盖 | 每个条件表达式的 True + False 都取过 | ✅ 推荐 |
| 路径覆盖 | 所有可能的执行路径都走过 | ⚠️ 复杂度指数增长，选关键路径 |

### 实操：如何从代码推导测试用例

```python
# 目标方法
def calculate_discount(price: float, is_vip: bool, quantity: int) -> float:
    if price <= 0:
        raise ValueError("价格必须为正数")
    
    discount = 0.0
    if is_vip:
        discount += 0.1
    if quantity >= 10:
        discount += 0.05
    elif quantity >= 5:
        discount += 0.02
    
    return round(price * (1 - discount), 2)
```

**推导过程**：

```
判定分析：
  ├── price <= 0           → True / False
  ├── is_vip               → True / False
  ├── quantity >= 10        → True / False
  └── quantity >= 5         → True / False（仅当 >= 10 为 False 时）

用例设计（判定覆盖）：
  1. price=-1, is_vip=False, quantity=1     → ValueError      [price<=0: T]
  2. price=100, is_vip=True, quantity=15    → 85.0             [vip: T, qty>=10: T]
  3. price=100, is_vip=False, quantity=7    → 98.0             [vip: F, qty>=5: T]
  4. price=100, is_vip=False, quantity=2    → 100.0            [vip: F, qty<5]
  5. price=100, is_vip=True, quantity=3     → 90.0             [vip: T, qty<5]

边界值：
  6. price=0.01                             → 最小有效价格
  7. quantity=5                             → 边界值
  8. quantity=10                            → 边界值
  9. quantity=9                             → 边界值 -1
```

---

## 1.3 测试结构规范

### Arrange-Act-Assert（AAA）模式

```python
def test_calculate_discount_vip_bulk():
    # Arrange — 准备测试数据和前置条件
    price = 100.0
    is_vip = True
    quantity = 15

    # Act — 执行目标方法
    result = calculate_discount(price, is_vip, quantity)

    # Assert — 验证预期输出
    assert result == 85.0  # 10% VIP + 5% 批量 = 15% 折扣
```

```typescript
describe('calculateDiscount', () => {
  it('should apply VIP + bulk discount', () => {
    // Arrange
    const price = 100;
    const isVip = true;
    const quantity = 15;

    // Act
    const result = calculateDiscount(price, isVip, quantity);

    // Assert
    expect(result).toBe(85.0);
  });
});
```

### 测试命名规范

格式：`test_{方法名}_{场景}_{预期结果}`

```python
def test_calculate_discount_negative_price_raises_error(): ...
def test_calculate_discount_vip_with_bulk_applies_both(): ...
def test_calculate_discount_non_vip_small_quantity_no_discount(): ...
```

### 测试组织

```
tests/
├── unit/
│   ├── test_order_service.py      # 对应 src/services/order_service.py
│   ├── test_discount_calc.py      # 对应 src/utils/discount_calc.py
│   └── test_user_validator.py     # 对应 src/validators/user_validator.py
├── integration/                   # Phase 2
└── system/                        # Phase 3
```

---

## 1.4 各技术栈测试框架

| 技术栈 | 框架 | Mock 库 | 运行命令 |
|--------|------|---------|----------|
| Python | pytest | unittest.mock / pytest-mock | `pytest tests/unit/ -v --cov=src --cov-report=term-missing` |
| TypeScript/JS | vitest / jest | 内置 Mock | `npx vitest run --coverage` |
| Java | JUnit 5 | Mockito | `mvn test -Dtest=*UnitTest` |
| Go | testing | 内置 / testify | `go test ./... -cover -v` |
| React | @testing-library/react | jest.fn() / vi.fn() | `npm test -- --coverage` |
| Vue | @vue/test-utils | vitest.fn() | `npx vitest run` |

---

## 1.5 覆盖率要求与解读

**目标**：不低于 70%（行覆盖率 + 分支覆盖率）。

覆盖率报告解读：

```
Name                     Stmts   Miss  Branch  BrPart  Cover
------------------------------------------------------------
src/services/order.py       85     12      24       4    82%
src/utils/discount.py       32      2       8       1    93%
src/validators/user.py      45     18      12       8    56%  ← 不达标
------------------------------------------------------------
TOTAL                      162     32      44      13    78%
```

**优先级**：先覆盖核心业务逻辑（Service/Domain），再覆盖工具类（Utils），最后覆盖胶水代码（Controller/Router）。

**不需要测的**：
- 纯 DTO/数据类（无逻辑）
- 框架生成代码（ORM 模型定义）
- 简单的委托方法（直接转发调用，无逻辑）

---

## 1.6 AI 执行单元测试的完整指令

给 AI 下达单元测试任务时，使用以下结构化指令：

```
## 单元测试任务

### 目标文件
{列出需要测试的源文件路径}

### 约束
- 覆盖率 ≥ 70%（行 + 分支）
- 使用白盒测试方法（判定覆盖 + 边界值分析）
- 每个测试用例遵循 AAA（Arrange-Act-Assert）模式
- 外部依赖全部 Mock（数据库、API 调用、文件系统）
- 测试命名格式：test_{方法名}_{场景}_{预期结果}

### 每个用例必须包含
1. 测试数据：明确的输入值
2. 前置条件：Mock 的返回值 / 环境状态
3. 测试步骤：调用目标方法
4. 预期输出：assert 断言（值 / 异常 / 副作用）

### 必须覆盖的场景
- 正常路径（happy path）
- 边界值（0, 1, 最大值, 空字符串, null/None）
- 异常路径（无效输入 → 预期异常）
- 分支组合（if/else 的 True + False 分支）

### 验证
- 运行测试并确保全部通过
- 输出覆盖率报告
- 标记未覆盖的行/分支并说明原因
```
