# Minecraft 插件自动化测试规范

## 技术栈与版本对齐

| 组件 | 版本 | 说明 |
|------|------|------|
| MockBukkit | `org.mockbukkit.mockbukkit:mockbukkit-v1.21:4.101.0` | 包名 `org.mockbukkit.mockbukkit`（非旧版 `be.seeseemelk`） |
| JUnit | 6.0.2 | MockBukkit 传递依赖，**不要手动声明 5.x 否则冲突** |
| Surefire | ≥3.5.2 | 低版本 JUnit 6 报 `OutputDirectoryCreator` 错 |
| Mockito | 5.11.0 | 与 JUnit 6 兼容 |
| SQLite JDBC | 3.45.1.0 | 内存数据库测试（test scope） |

### Maven 仓库

```xml
<repositories>
    <repository>
        <id>papermc</id>
        <url>https://repo.papermc.io/repository/maven-public/</url>
    </repository>
</repositories>
```

### 方式一：McTestHarness（推荐）

封装 MockBukkit + Mockito + SQLite + 断言工具 + 外部插件 Mock 工厂，一个依赖搞定。

```xml
<dependency>
    <groupId>cn.drcomo</groupId>
    <artifactId>McTestHarness</artifactId>
    <version>1.0.0</version>
    <scope>test</scope>
</dependency>
```

> 已安装到本地 Maven 仓库，任何本地 MC 插件项目可直接引用。

### 方式二：手动引入

```xml
<dependency>
    <groupId>org.mockbukkit.mockbukkit</groupId>
    <artifactId>mockbukkit-v1.21</artifactId>
    <version>4.101.0</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-core</artifactId>
    <version>5.11.0</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.xerial</groupId>
    <artifactId>sqlite-jdbc</artifactId>
    <version>3.45.1.0</version>
    <scope>test</scope>
</dependency>
```

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <version>3.5.2</version>
</plugin>
```

> **关键**：不要显式声明 `junit-jupiter:5.x`，否则与 MockBukkit 传递的 6.0.2 冲突。

---

## 测试分层

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元测试 | 领域对象/工具类/配置解析/序列化 | JUnit + 断言 |
| 服务层测试 | Service 业务逻辑 | MockBukkit + Mockito |
| 集成测试 | DB 读写/菜单交互/命令/事件触发 | MockBukkit + SQLite 内存库 |
| 回归测试 | 修复的 Bug 须有测试防复发 | 同上 |

---

## 外部插件 Mock（禁止加载真实 jar）

```java
// Vault Economy
Economy mockEconomy = Mockito.mock(Economy.class);
server.getServicesManager().register(Economy.class, mockEconomy, plugin, ServicePriority.Normal);

// PlaceholderAPI
PluginMock papi = MockBukkit.createMockPlugin("PlaceholderAPI");

// 其他外部插件：Mock 接口，注入 Adapter
```

---

## 测试基类

### 使用 McTestHarness

```java
import cn.drcomo.testharness.McPluginTestBase;

class MyCraftServiceTest extends McPluginTestBase<MyPlugin> {
    @Override
    protected Class<MyPlugin> pluginClass() { return MyPlugin.class; }

    @Override
    protected void beforePluginLoad() {
        // 可选：注册外部插件 Mock（在 plugin 加载前）
    }

    @Test
    void shouldDoSomething() {
        advanceTicks(20); // 推进 1 秒
    }
}
```

```java
import cn.drcomo.testharness.McIntegrationTestBase;

class MyStorageTest extends McIntegrationTestBase<MyPlugin> {
    @Override
    protected Class<MyPlugin> pluginClass() { return MyPlugin.class; }

    @Override
    protected void beforePluginLoad() {
        mocks.registerVaultEconomy(server);
        mocks.registerPlaceholderAPI(server);
    }

    @Test
    void shouldPersistData() throws Exception {
        executeSql("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)");
    }
}
```

### 手动基类

```java
public abstract class McPluginTestBase {
    protected ServerMock server;
    protected MyPlugin plugin;
    protected PlayerMock player;

    @BeforeEach
    void setUp() {
        server = MockBukkit.mock();
        plugin = MockBukkit.load(MyPlugin.class);
        player = server.addPlayer();
    }

    @AfterEach
    void tearDown() {
        MockBukkit.unmock();
    }
}
```

### 手动集成测试基类（含外部插件 Mock + 数据库）

```java
public abstract class McIntegrationTestBase {
    protected ServerMock server;
    protected MyPlugin plugin;
    protected PlayerMock player;
    protected Economy mockEconomy;
    protected Connection dbConnection;

    @BeforeEach
    void setUp() throws Exception {
        server = MockBukkit.mock();
        // Vault Economy Mock
        mockEconomy = Mockito.mock(Economy.class);
        Mockito.when(mockEconomy.isEnabled()).thenReturn(true);
        Mockito.when(mockEconomy.depositPlayer(Mockito.any(), Mockito.anyDouble()))
                .thenAnswer(inv -> new EconomyResponse(
                        inv.getArgument(1), 1000.0,
                        EconomyResponse.ResponseType.SUCCESS, ""));
        Mockito.when(mockEconomy.withdrawPlayer(Mockito.any(), Mockito.anyDouble()))
                .thenAnswer(inv -> new EconomyResponse(
                        inv.getArgument(1), 1000.0,
                        EconomyResponse.ResponseType.SUCCESS, ""));
        MockBukkit.createMockPlugin("PlaceholderAPI");
        plugin = MockBukkit.load(MyPlugin.class);
        player = server.addPlayer();
        // SQLite 内存库
        SQLiteDataSource ds = new SQLiteDataSource();
        ds.setUrl("jdbc:sqlite::memory:");
        dbConnection = ds.getConnection();
    }

    @AfterEach
    void tearDown() throws Exception {
        if (dbConnection != null && !dbConnection.isClosed()) dbConnection.close();
        MockBukkit.unmock();
    }
}
```
