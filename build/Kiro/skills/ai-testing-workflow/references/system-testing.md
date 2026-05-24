# Phase 3 — 系统测试与确认测试

整个系统部署完毕后的端到端验证。依赖真实环境，不使用 Mock。

---

## 3.1 系统测试 vs 集成测试

| 维度 | 集成测试 | 系统测试 |
|------|----------|----------|
| 环境 | 局部，部分 Mock | 全系统部署，真实依赖 |
| 视角 | 开发者：模块协作对不对 | 用户：功能能不能用 |
| 数据 | 测试数据 / Mock 数据 | 接近真实的完整数据集 |
| 前端 | Mock API 层 | 真实浏览器交互 |
| 发现的问题 | 接口不匹配 | 部署配置、性能瓶颈、跨系统集成错误 |

---

## 3.2 系统测试分类

### 3.2.1 API/接口测试（灰盒）

针对后端 API 的黑盒请求 + 数据库状态验证。

**测试策略**：

```
1. 准备测试数据（seed 或 fixture）
2. 通过 HTTP 请求调用 API
3. 验证响应状态码 + 响应体
4. 验证数据库状态变更
5. 验证跨 API 的数据一致性
```

**Python（httpx / requests）示例**：

```python
"""系统测试 — 订单完整流程"""
import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"

class TestOrderSystemFlow:
    """验证订单从创建到完成的完整链路"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """前置条件：系统已启动，测试用户已存在"""
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            # 确认系统健康
            r = await client.get("/health")
            assert r.status_code == 200
            self.client = client
            yield

    async def test_full_order_lifecycle(self):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
            # Step 1: 创建订单
            r = await c.post("/api/orders", json={
                "user_id": "test-user-1",
                "items": [{"sku": "PROD-001", "quantity": 2}]
            })
            assert r.status_code == 201
            order = r.json()["data"]
            order_id = order["id"]

            # Step 2: 确认订单状态
            r = await c.get(f"/api/orders/{order_id}")
            assert r.status_code == 200
            assert r.json()["data"]["status"] == "pending"

            # Step 3: 支付
            r = await c.post(f"/api/orders/{order_id}/pay", json={
                "method": "test_card",
                "amount": order["total"]
            })
            assert r.status_code == 200

            # Step 4: 验证最终状态
            r = await c.get(f"/api/orders/{order_id}")
            assert r.json()["data"]["status"] == "paid"
```

### 3.2.2 界面测试（前端系统测试）

使用 Playwright / Selenium 进行真实浏览器自动化测试。

**Playwright 是首选**（相比 Selenium：更快、更稳定、API 更现代）。

**核心概念**：
- Playwright 通过解析 DOM 树定位元素并模拟用户操作
- 每次操作（点击、输入）后会等待 DOM 稳定再继续
- 可以截图、录屏用于失败分析

**Playwright 定位器策略**（优先级从高到低）：

| 策略 | 示例 | 优先级 |
|------|------|--------|
| Role + Name | `page.getByRole('button', { name: '提交' })` | ✅ 首选 |
| Test ID | `page.getByTestId('submit-btn')` | ✅ 推荐 |
| Label | `page.getByLabel('用户名')` | ✅ 推荐 |
| Text | `page.getByText('登录成功')` | ✅ 验证用 |
| CSS Selector | `page.locator('.btn-primary')` | ⚠️ 备选 |
| XPath | `page.locator('//div[@class="x"]')` | ❌ 尽量避免 |

**关键问题：AI 只关注被点击元素的变化，忽略副作用**

这是 AI 做 UI 测试的常见盲区。解决方案：

```typescript
// ❌ AI 典型写法 — 只验证按钮本身
test('click submit button', async ({ page }) => {
  await page.getByRole('button', { name: '提交' }).click();
  // 只检查了按钮，没检查页面其他变化
  await expect(page.getByRole('button', { name: '提交' })).toBeDisabled();
});

// ✓ 正确写法 — 验证操作的所有可观察效果
test('submit order updates page state', async ({ page }) => {
  await page.getByRole('button', { name: '提交' }).click();

  // 1. 按钮状态变化
  await expect(page.getByRole('button', { name: '提交' })).toBeDisabled();
  // 2. 加载指示器出现
  await expect(page.getByTestId('loading-spinner')).toBeVisible();
  // 3. 成功后：提示消息
  await expect(page.getByText('订单已提交')).toBeVisible({ timeout: 10000 });
  // 4. 列表更新
  await expect(page.getByTestId('order-list').locator('li')).toHaveCount(3);
  // 5. 导航变化
  await expect(page).toHaveURL(/\/orders\/\d+/);
});
```

**AI 提示词要求**（强制包含）：

```
每个 UI 测试用例必须验证操作的所有可观察副作用：
1. 被操作元素自身的状态变化
2. 页面上其他受影响元素的状态变化
3. URL 变化（如有）
4. 网络请求是否发出（如有）
5. 新元素的出现/消失
```

**Playwright 测试结构**：

```typescript
import { test, expect } from '@playwright/test';

test.describe('订单管理', () => {
  test.beforeEach(async ({ page }) => {
    // 前置条件：登录 + 导航到目标页面
    await page.goto('/login');
    await page.getByLabel('用户名').fill('test_user');
    await page.getByLabel('密码').fill('test_pass');
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForURL('/dashboard');
  });

  test('创建订单完整流程', async ({ page }) => {
    // Step 1: 导航到创建页
    await page.getByRole('link', { name: '新建订单' }).click();
    await expect(page).toHaveURL('/orders/new');

    // Step 2: 填写表单
    await page.getByLabel('商品').selectOption('PROD-001');
    await page.getByLabel('数量').fill('3');

    // Step 3: 提交
    await page.getByRole('button', { name: '提交订单' }).click();

    // Step 4: 验证所有副作用
    await expect(page.getByText('订单创建成功')).toBeVisible();
    await expect(page).toHaveURL(/\/orders\/\d+/);
    await expect(page.getByTestId('order-status')).toHaveText('待支付');
    await expect(page.getByTestId('order-total')).toContainText('¥');
  });

  test('删除订单更新列表', async ({ page }) => {
    await page.goto('/orders');
    const initialCount = await page.getByTestId('order-row').count();

    // 删除第一个订单
    await page.getByTestId('order-row').first().getByRole('button', { name: '删除' }).click();
    await page.getByRole('button', { name: '确认删除' }).click();

    // 验证：列表减少 + 提示出现 + 被删订单消失
    await expect(page.getByTestId('order-row')).toHaveCount(initialCount - 1);
    await expect(page.getByText('删除成功')).toBeVisible();
  });
});
```

### 3.2.3 E2E 管线测试

对于多阶段处理管线（AI/LLM、ETL、微服务链路），需要逐阶段运行真实请求并验证。

**核心前提**：静态通过 ≠ 可用。静态检查只覆盖语法和类型，以下类别只有运行时才会暴露：

| 类别 | 示例 |
|------|------|
| 环境依赖 | 缺包、端口冲突、代理配置、环境变量缺失 |
| 数据契约 | LLM 输出格式不稳定、JSON 解析失败、字段嵌套错误 |
| 并发/异步 | 后台任务未完成就查询、DB 写锁冲突 |
| 跨模块耦合 | 函数签名变更但调用方未同步、Repository 方法参数不匹配 |
| 状态累积 | 旧测试数据污染新查询、Job 状态机卡死 |

#### E2E Step 1 — 侦察管线

**识别管线阶段**，画出完整的阶段流转图：

搜索策略（并行执行）：
```
1. 路由层搜索：grep -r "@router\.(get|post)" --include="*.py" 或搜 router/routes
2. API 文档搜索：grep -r "openapi|swagger|/docs" 或访问 /docs 端点
3. 前端调用链搜索：grep -r "fetch\|axios\|apiRequest" --include="*.ts"
4. 工作流/Pipeline 关键词：grep -r "pipeline|workflow|stage|step|phase"
```

**产出**：阶段图 + 每阶段的 `输入 → 处理 → 输出` 三元组。

```
parse → enrich → generate-job → poll-status → get-result
  ↓        ↓          ↓              ↓            ↓
POST    POST      POST           GET(loop)     GET
```

**定位测试数据**（优先顺序）：
1. 已有测试数据（DB 中的现有记录）
2. 项目示例数据（fixtures、seeds、examples/）
3. 自构造最小数据（仅在以上都不存在时）

#### E2E Step 2 — 构建测试脚手架

编写独立的异步测试脚本，按管线阶段顺序编排请求：

```python
"""E2E Pipeline Test — {管线名称}"""
import asyncio, httpx, time, json, os

BASE = "http://127.0.0.1:{PORT}"
# 清除可能干扰的代理环境变量
for var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(var, None)

async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=120) as c:
        # ── Stage 1 ──
        print(f"\n[STEP 1] {阶段名称}")
        t0 = time.time()
        r = await c.post("/api/xxx", json={...})
        elapsed = time.time() - t0
        print(f"  Status: {r.status_code} ({elapsed:.1f}s)")

        if r.status_code != 200:
            print(f"  ERROR: {r.text[:200]}")
            return  # 阻塞：不继续后续阶段

        data = r.json()
        print(f"  Key field: {data.get('some_field')}")

        # ── 轮询型阶段 ──
        for i in range(60):
            r = await c.get(f"/api/jobs/{job_id}")
            status = r.json()
            if status["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(5)

    print(f"\n{'='*60}\nE2E TEST {'PASSED ✓' if success else 'FAILED ✗'}")

asyncio.run(main())
```

**关键原则**：
- 每阶段打印 status code + 耗时 + 关键输出字段
- 上游失败立即停止，不浪费时间跑下游
- 轮询阶段有上限和间隔
- 清除代理环境变量（常见陷阱）

**启动测试前逐项检查**：
```
□ 服务端口是否被占用？  → netstat -ano | findstr ":{PORT}"
□ 依赖是否完整？        → pip list | grep {关键包}
□ .env 文件是否存在？
□ DB 是否可访问？
□ 外部服务是否可达？
```

#### E2E Step 3 — 逐阶段运行与修复循环

启动服务（必须用 `--reload`，调试阶段可自动加载代码改动）：

```bash
uvicorn app.main:app --host 127.0.0.1 --port {PORT} --reload
```

核心循环：

```
运行测试脚本
    ↓
某阶段失败
    ↓
查看两个信息源：
  ├── 测试脚本输出（status code + error message）
  └── 服务端日志（traceback + 上下文日志）
    ↓
定位根因（见诊断决策树）
    ↓
最小化修复（只改导致失败的代码）
    ↓
重跑测试
```

**诊断决策树**：

```
错误类型?
├── ImportError / ModuleNotFoundError
│   → 缺包：安装缺失依赖
│   → 缺导入：在文件头部添加 import
├── TypeError: xxx() got an unexpected keyword argument
│   → 函数签名变更但调用方未同步
├── 500 Internal Server Error（无 traceback）
│   → 查服务端终端日志
├── JSON 解析失败（LLM 管线最常见）
│   → 打印原始输出 → 判断截断还是格式错误
│   → 截断 → 增大 max_tokens
│   → 格式错误 → 加 retry 逻辑
├── 连接拒绝 / 超时
│   → 端口 / 代理环境变量 / 服务未启动
└── 数据不一致
    → 旧数据污染 / 字段嵌套错误 / 默认值缺失
```

**LLM 输出防御策略**：

| 问题 | 防御措施 |
|------|----------|
| 输出被截断 | `max_tokens` 设为预估输出长度的 2 倍 |
| JSON 格式不稳定 | retry 循环（3 次），每次重试加"只返回纯 JSON" |
| CJK 引号破坏 JSON | 先试 raw `json.loads`，再试清理后版本 |
| 字段缺失/多余 | `.get()` + 默认值 |
| 嵌套结构异常 | 递归 flatten 逻辑 |

#### E2E Step 4 — 全管线验证

成功标准：
```
□ 每个阶段返回 2xx
□ 每个阶段输出包含预期字段且值非空
□ 轮询型阶段最终状态为 completed
□ 最终输出与输入数据在语义上一致
□ 服务端日志无 ERROR 级别异常
```

LLM 管线具有随机性，至少运行 2-3 次确认稳定性。

验证完主路径后覆盖其他分支：不同输入格式、可选参数组合、错误输入的优雅降级、并行请求冲突。

#### E2E 常见陷阱速查

| 陷阱 | 症状 | 解法 |
|------|------|------|
| 端口冲突 | `Address already in use` | `netstat -ano \| findstr ":{PORT}"` → kill |
| 代理干扰 | `ConnectError` 到 localhost | 清除 `HTTP_PROXY` 等环境变量 |
| 旧进程残留 | 改了代码但行为不变 | 确认 PID 是新进程；用 `--reload` |
| DB 旧数据污染 | 结果混合了无关数据 | 加时间/Job 过滤条件 |
| LLM 输出格式漂移 | 同一 prompt 有时成功有时失败 | retry + 降温度 + 强化格式要求 |

---

## 3.3 确认测试（Acceptance Testing）

确认测试面向客户/用户，验证系统是否满足需求规格。

### 与系统测试的区别

| 维度 | 系统测试 | 确认测试 |
|------|----------|----------|
| 视角 | 技术团队：功能对不对 | 客户/用户：满不满足需求 |
| 用例来源 | 技术规格 / API 设计 | 用户故事 / 验收标准 |
| 通过标准 | 无 Bug、性能达标 | 客户签字确认 |
| 数据 | 测试数据 | 真实业务数据（或高仿真） |

### 确认测试用例格式

```gherkin
Feature: 订单管理
  作为一个购物用户
  我希望能创建和管理订单
  以便完成购物流程

  Scenario: 成功创建订单
    Given 用户已登录且购物车有 2 件商品
    When 用户点击"提交订单"
    Then 页面显示"订单创建成功"
    And 订单状态为"待支付"
    And 购物车清空

  Scenario: 库存不足时拒绝下单
    Given 用户已登录且购物车有 1 件库存为 0 的商品
    When 用户点击"提交订单"
    Then 页面显示"库存不足，无法下单"
    And 购物车保持不变
```

**AI 执行确认测试时**：将 Gherkin 场景转化为 Playwright 测试或 API 测试脚本。

---

## 3.4 CI/CD 集成

测试应作为 CI/CD 管线的一部分自动执行。

### 测试执行顺序（CI 管线）

```yaml
# .github/workflows/test.yml 或 其他 CI 配置
stages:
  - lint          # 静态检查（eslint/ruff/mypy）
  - unit-test     # 单元测试（最快，先跑）
  - integration   # 集成测试（需要测试 DB）
  - build         # 构建
  - system-test   # 系统测试（需要部署，最后跑）
```

**原则**：
- 快速反馈：单元测试 < 2 分钟，集成测试 < 5 分钟
- 失败即停：前一阶段失败不跑后一阶段
- 并行化：同一阶段的独立测试套件并行执行

### 各阶段触发条件

| 阶段 | 触发条件 | 时机 |
|------|----------|------|
| 单元测试 | 每次 commit / PR | 开发中 |
| 集成测试 | 每次 PR / merge 到主分支 | 合并前 |
| 系统测试 | 部署到 staging 后 | 发布前 |
| 确认测试 | 部署到 UAT 环境后 | 上线前 |

---

## 3.5 AI 执行系统测试的完整指令

```
## 系统测试任务

### 环境要求
- 系统已完整部署并可访问
- 测试数据已准备（或 seed 脚本可用）
- {前端地址} / {后端 API 地址}

### 后端 API 测试
- 对所有 RESTful 端点编写系统测试
- 验证完整业务流程（创建 → 查询 → 更新 → 删除）
- 验证跨端点数据一致性
- 验证错误场景的优雅降级（400/404/422）
- 使用真实 HTTP 请求，不 Mock

### 前端界面测试（Playwright）
- 对所有用户可见页面编写 UI 测试
- 每个操作必须验证所有可观察副作用（不只是被操作元素）：
  * 被操作元素自身的状态变化
  * 页面上其他受影响元素的变化
  * URL 变化
  * 新元素出现/消失
  * 数据列表更新
- 使用 Role / TestID / Label 定位器（禁止 XPath）
- 覆盖：正常流程 + 异常流程 + 边界操作

### 确认测试
- 将用户故事转化为可执行测试
- 使用 Given-When-Then 格式描述场景
- 验证端到端业务流程的完整性

### 验证
- 所有测试在真实环境中通过
- 无 500 错误
- 界面测试截图保存用于回溯
```
