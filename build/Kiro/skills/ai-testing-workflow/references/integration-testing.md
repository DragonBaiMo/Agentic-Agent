# Phase 2 — 集成测试

验证模块之间的协作是否正确。单个方法都通过仍可能在模块交互时出错。

---

## 2.1 集成测试 vs 单元测试

| 维度 | 单元测试 | 集成测试 |
|------|----------|----------|
| 测试对象 | 单个方法/函数 | 模块间交互（类与类、服务与服务） |
| 依赖处理 | 全部 Mock | 部分真实 + 部分 Mock |
| 速度 | 极快（毫秒级） | 较慢（可能涉及 DB/网络） |
| 发现的问题 | 逻辑错误、边界错误 | 接口不匹配、数据契约断裂、集成点错误 |
| 失败告诉你什么 | 这个方法逻辑有 Bug | 两个模块的协作方式有问题 |

---

## 2.2 Mock 核心概念

### 什么时候 Mock

| 场景 | 是否 Mock | 原因 |
|------|-----------|------|
| 外部 API 调用 | ✅ Mock | 不可控、不确定、有成本 |
| 数据库访问 | 条件性 | 简单查询可用测试 DB；复杂场景 Mock Repository 层 |
| 文件系统 | ✅ Mock | 避免测试间污染 |
| 定时器/时间 | ✅ Mock | 确保测试可重复 |
| 同项目的其他模块 | ❌ 不 Mock | 集成测试的核心就是验证真实交互 |
| LLM/AI 服务 | ✅ Mock | 输出非确定性、有成本 |

### Mock 三件套

| 工具 | 作用 | 使用场景 |
|------|------|----------|
| **Mock** | 替代真实对象，可验证调用（被调用了吗？参数对吗？调了几次？） | 需要验证交互行为 |
| **Stub** | 替代真实对象，返回预设值（不关心调用细节） | 只需控制依赖的返回值 |
| **Spy** | 包装真实对象，记录调用但仍执行真实逻辑 | 需要真实行为 + 调用记录 |

---

## 2.3 依赖倒置是 Mock 的前提

**核心问题**：如果代码在方法体内直接 `new` 一个依赖对象，Mock 极其困难。

```python
# ❌ 硬编码依赖 — Mock 困难
class OrderService:
    def create_order(self, data):
        repo = OrderRepository()          # 在方法体内实例化
        validator = OrderValidator()      # 在方法体内实例化
        validator.validate(data)
        return repo.save(data)

# 测试时无法替换 repo 和 validator，因为它们在方法内部创建

# ✓ 依赖注入 — Mock 轻松
class OrderService:
    def __init__(self, repo: IOrderRepository, validator: IOrderValidator):
        self._repo = repo
        self._validator = validator

    def create_order(self, data):
        self._validator.validate(data)
        return self._repo.save(data)

# 测试时：
mock_repo = Mock(spec=IOrderRepository)
mock_validator = Mock(spec=IOrderValidator)
service = OrderService(mock_repo, mock_validator)
# 完全可控
```

```typescript
// ❌ 硬编码
class OrderService {
  private repo = new OrderRepository();  // 无法替换

  async createOrder(data: OrderInput) {
    return this.repo.save(data);
  }
}

// ✓ 注入
class OrderService {
  constructor(private repo: IOrderRepository) {}

  async createOrder(data: OrderInput) {
    return this.repo.save(data);
  }
}

// 测试时：
const mockRepo = { save: vi.fn().mockResolvedValue({ id: '1', ...data }) };
const service = new OrderService(mockRepo);
```

**若发现代码存在硬编码依赖** → 先执行 Phase 0（可测试性重构），再回到 Phase 2。

---

## 2.4 集成测试策略

### 后端集成测试

**典型测试层级**：

```
Controller ←→ Service ←→ Repository ←→ Database
    层                    层                层
```

| 集成点 | 怎么测 | Mock 什么 |
|--------|--------|-----------|
| Service → Repository | 注入真实 Repository，连测试 DB | 外部 API |
| Controller → Service | 发 HTTP 请求到 Controller | DB（用内存 DB 或 Mock Repository） |
| Service → 外部 API | 注入 Mock 的 API Client | API Client |
| 多 Service 协作 | 注入真实 Service，Mock 最外层依赖 | DB / 外部 API |

**Python（FastAPI + pytest）示例**：

```python
import pytest
from unittest.mock import AsyncMock, Mock
from app.services.order_service import OrderService
from app.repositories.order_repo import OrderRepository

@pytest.fixture
def mock_external_api():
    """Mock 外部支付 API"""
    api = AsyncMock()
    api.charge.return_value = {"status": "success", "tx_id": "tx-123"}
    return api

@pytest.fixture
def order_service(mock_external_api):
    """真实 Repository + Mock 外部 API"""
    repo = OrderRepository(db_url="sqlite:///test.db")  # 测试 DB
    return OrderService(repo=repo, payment_api=mock_external_api)

async def test_create_order_charges_payment(order_service, mock_external_api):
    # Arrange
    order_data = {"user_id": "u1", "items": [{"sku": "A1", "qty": 2}], "total": 99.0}

    # Act
    result = await order_service.create_order(order_data)

    # Assert — 验证模块交互
    assert result.status == "confirmed"
    mock_external_api.charge.assert_called_once_with(amount=99.0, currency="CNY")
    # 验证 DB 中确实写入了
    saved = await order_service.get_order(result.id)
    assert saved is not None
    assert saved.total == 99.0
```

**TypeScript（vitest）示例**：

```typescript
describe('OrderService integration', () => {
  it('should create order and call payment API', async () => {
    // Arrange — 真实 service，Mock 外部 API
    const mockPayment: IPaymentAPI = {
      charge: vi.fn().mockResolvedValue({ status: 'success', txId: 'tx-123' }),
    };
    const repo = new InMemoryOrderRepository(); // 内存实现
    const service = new OrderService(repo, mockPayment);

    // Act
    const result = await service.createOrder({
      userId: 'u1',
      items: [{ sku: 'A1', qty: 2 }],
      total: 99.0,
    });

    // Assert
    expect(result.status).toBe('confirmed');
    expect(mockPayment.charge).toHaveBeenCalledWith({ amount: 99.0, currency: 'CNY' });
    expect(await repo.findById(result.id)).toBeDefined();
  });
});
```

### 前端集成测试

**典型测试层级**：

```
Component ←→ Store/Hook ←→ API Service ←→ Backend
    层               层              层
```

| 集成点 | 怎么测 | Mock 什么 |
|--------|--------|-----------|
| Component → Store/Hook | 渲染组件 + 操作 → 验证状态变化 | API 层 |
| Store → API Service | 直接调用 Store Action → 验证状态 | HTTP 请求 |
| 组件交互链 | 多组件渲染 → 操作 A → 验证 B 的状态 | API 层 |

**React（@testing-library/react + vitest）示例**：

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OrderPage } from './OrderPage';

// Mock API 层
vi.mock('@/api/orderApi', () => ({
  createOrder: vi.fn().mockResolvedValue({ id: '1', status: 'confirmed' }),
}));

describe('OrderPage integration', () => {
  it('should submit order and show confirmation', async () => {
    render(<OrderPage />);

    // 用户操作
    fireEvent.change(screen.getByLabelText('商品数量'), { target: { value: '3' } });
    fireEvent.click(screen.getByText('提交订单'));

    // 验证页面状态变化
    await waitFor(() => {
      expect(screen.getByText('订单已确认')).toBeInTheDocument();
    });
  });

  it('should show error on API failure', async () => {
    const { createOrder } = await import('@/api/orderApi');
    (createOrder as Mock).mockRejectedValueOnce(new Error('网络错误'));

    render(<OrderPage />);
    fireEvent.click(screen.getByText('提交订单'));

    await waitFor(() => {
      expect(screen.getByText('提交失败')).toBeInTheDocument();
    });
  });
});
```

### 状态机测试（前端特有）

当组件有复杂状态转换时，用状态机穷举测试：

```typescript
describe('OrderStateMachine', () => {
  const transitions = [
    { from: 'idle',       event: 'submit',    to: 'submitting' },
    { from: 'submitting', event: 'success',   to: 'confirmed'  },
    { from: 'submitting', event: 'failure',   to: 'error'      },
    { from: 'error',      event: 'retry',     to: 'submitting' },
    { from: 'confirmed',  event: 'reset',     to: 'idle'       },
  ];

  transitions.forEach(({ from, event, to }) => {
    it(`should transition from ${from} to ${to} on ${event}`, () => {
      const machine = createOrderMachine(from);
      const result = machine.send(event);
      expect(result.state).toBe(to);
    });
  });

  // 非法转换
  it('should not transition from confirmed on submit', () => {
    const machine = createOrderMachine('confirmed');
    expect(() => machine.send('submit')).toThrow();
  });
});
```

---

## 2.5 AI 执行集成测试的完整指令

```
## 集成测试任务

### 目标模块
{列出需要测试的模块交互对}

### 前置检查
- 确认代码遵循依赖倒置原则（可 Mock）
- 若存在硬编码依赖 → 先重构（参考 Phase 0）

### 约束
- 同项目模块之间使用真实实现，不 Mock
- 外部依赖（DB/API/文件系统）使用 Mock 或测试替身
- 每个测试用例验证模块交互行为（调用参数、调用顺序、状态变更）
- 覆盖正常交互 + 异常交互（依赖返回错误时的处理）

### Mock 规则
- 使用 Mock/Stub/Spy 明确区分意图
- Mock 必须基于接口/抽象类，不 Mock 具体实现
- Mock 返回值必须符合真实接口的 Schema

### 前端额外要求
- 组件集成测试：渲染 → 用户操作 → 验证状态变化
- 状态机覆盖：列出所有状态转换，逐一验证
- Mock API 层，不 Mock Store/Hook

### 验证
- 运行测试并确保全部通过
- 确认 Mock 的调用断言正确（不漏不多）
```
