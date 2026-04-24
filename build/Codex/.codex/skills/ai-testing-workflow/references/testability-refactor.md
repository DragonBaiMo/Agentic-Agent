# Phase 0 — 可测试性重构

在编写任何测试之前，代码本身必须具备可测试性。不可测试的代码写再多测试也只是表面覆盖。

---

## 0.1 可测试性评估

对目标代码进行快速扫描，识别阻碍测试的结构性问题：

| 阻碍 | 症状 | 严重度 |
|------|------|--------|
| 硬编码依赖 | 方法体内 `new XXX()` / 直接实例化外部类 | 🔴 高 |
| 全局状态 | 静态变量 / 单例滥用 / 全局 mutable 对象 | 🔴 高 |
| 巨型方法 | 单方法 > 50 行，混合 I/O + 业务逻辑 + 数据转换 | 🟡 中 |
| 隐式依赖 | 方法内部读环境变量 / 读文件 / 访问数据库 | 🟡 中 |
| 紧耦合模块 | 模块 A 直接 import B 的内部实现而非接口 | 🟡 中 |
| 缺少接口抽象 | 类之间直接依赖具体实现，无接口/抽象层 | 🟡 中 |

**产出**：一份问题清单，按严重度排序。

---

## 0.2 SOLID 原则应用

重构时遵循 SOLID 五原则，每条原则的可测试性含义：

### S — 单一职责（Single Responsibility）

**规则**：一个类/模块只有一个变更理由。

**可测试性影响**：职责单一的类测试用例少、断言清晰、Mock 少。

**操作**：
- 识别承担多职责的类 → 按职责拆分
- 判断标准：如果类名需要用 "And" 连接两个描述，则违反 SRP

```
# ❌ 违反 SRP
class OrderService:
    def create_order(self, data): ...      # 订单创建
    def send_email(self, order): ...       # 邮件发送
    def generate_report(self, orders): ... # 报表生成

# ✓ 遵循 SRP
class OrderService:
    def create_order(self, data): ...

class OrderNotifier:
    def send_email(self, order): ...

class OrderReporter:
    def generate_report(self, orders): ...
```

### O — 开闭原则（Open/Closed）

**规则**：对扩展开放，对修改关闭。

**可测试性影响**：新增功能不改已有代码 → 已有测试不会被破坏。

**操作**：识别需要频繁修改的 `if/else` 或 `switch` 链 → 抽象为策略/多态。

### L — 里氏替换（Liskov Substitution）

**规则**：子类型必须能替换父类型而不破坏行为。

**可测试性影响**：Mock 对象替换真实对象时，行为契约一致。

### I — 接口隔离（Interface Segregation）

**规则**：不强迫依赖方依赖它不需要的方法。

**可测试性影响**：小接口 → Mock 更轻量，测试更聚焦。

### D — 依赖倒置（Dependency Inversion）⭐ 最关键

**规则**：高层模块不依赖低层模块实现，二者都依赖抽象。

**可测试性影响**：这是 Mock 能否工作的根本前提。

```python
# ❌ 硬编码依赖 — 无法 Mock
class OrderService:
    def process(self, order_id):
        db = MySQLDatabase()          # 硬编码实例化
        order = db.query(order_id)    # 无法替换为测试 DB
        notifier = EmailNotifier()    # 硬编码实例化
        notifier.send(order)          # 无法替换为假通知器

# ✓ 依赖倒置 — 可 Mock
class OrderService:
    def __init__(self, db: Database, notifier: Notifier):  # 通过构造器注入
        self._db = db
        self._notifier = notifier

    def process(self, order_id):
        order = self._db.query(order_id)      # 测试时注入 MockDB
        self._notifier.send(order)             # 测试时注入 MockNotifier
```

```typescript
// ❌ 硬编码依赖
class UserController {
  private service = new UserService(); // 无法替换
  async getUser(id: string) {
    return this.service.findById(id);
  }
}

// ✓ 依赖注入
class UserController {
  constructor(private service: IUserService) {} // 接口注入
  async getUser(id: string) {
    return this.service.findById(id);
  }
}
```

**依赖注入三种方式**（按优先级）：

| 方式 | 适用场景 | 示例 |
|------|----------|------|
| 构造器注入 | 默认选择，生命周期一致的依赖 | `__init__(self, db: Database)` |
| 方法参数注入 | 仅某个方法需要的临时依赖 | `def process(self, data, parser: Parser)` |
| 属性/Setter 注入 | 框架要求或可选依赖 | `@Inject() service: IService` |

---

## 0.3 设计模式探索

在应用了 SOLID 原则后，根据代码的实际问题选择主流设计模式。

**AI 操作指令**：
1. 探索项目代码结构，识别重复模式和耦合点
2. 根据实际问题匹配设计模式（不是为了用模式而用模式）
3. 目标：**高内聚、低耦合**

### 常用设计模式与适用场景

| 模式 | 适用场景 | 可测试性收益 |
|------|----------|-------------|
| **策略模式** | 多种算法/行为可互换 | 每种策略独立测试 |
| **工厂模式** | 对象创建逻辑复杂 | 创建逻辑集中，可 Mock 工厂 |
| **观察者模式** | 事件通知、状态变更传播 | 发布/订阅方各自独立测试 |
| **适配器模式** | 对接第三方库/旧接口 | 适配层可用 Mock 替换 |
| **装饰器模式** | 动态增加职责 | 核心逻辑与附加逻辑分离测试 |
| **仓储模式** | 数据访问层抽象 | 业务逻辑不依赖具体数据库 |
| **命令模式** | 操作封装、撤销/重做 | 每个命令独立测试 |

**操作步骤**：

```
1. 扫描代码 → 列出耦合热点
2. 对每个热点判断：哪种设计模式能降低耦合？
3. 重构时保持现有功能不变（先有测试保护，再重构）
4. 验证重构后功能与重构前一致
```

---

## 0.4 前后端分离的可测试性要求

若项目需要前后端分离或已分离：

### 后端

- API 遵循 RESTful 规范，资源用复数名词
- 请求/响应有明确的 Schema 定义（Pydantic / Zod / JSON Schema）
- 业务逻辑与框架解耦（Controller 薄层 → Service 厚层 → Repository 数据层）
- 每层通过接口依赖上层，便于单独 Mock 测试

### 前端

- 组件与状态管理分离（React: hooks/store 与 UI 组件分离）
- API 调用层抽象为独立 Service（不在组件内直接 fetch）
- 状态机/有限状态自动机用于复杂交互（便于穷举测试）
- 纯 UI 渲染与副作用分离

---

## 0.5 重构执行协议

**核心原则**：先有测试保护，再重构。没有测试的重构是冒险。

**执行顺序**：

```
1. 对现有代码写最小覆盖的"特征测试"（验证当前行为，不管对错）
2. 应用 SOLID 原则重构
3. 探索并应用合适的设计模式
4. 每次重构后运行特征测试，确保行为不变
5. 重构完成后，再按 Phase 1-3 写正式测试
```

**禁止**：
- 重构时同时改业务逻辑
- 没有任何测试保护就大规模重构
- 为了用设计模式而过度抽象（YAGNI）
