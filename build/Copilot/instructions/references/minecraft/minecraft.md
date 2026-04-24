# Minecraft 插件开发规范

> 本文件是领域特化补充。通用编码规范见主文件 `code-quality.instructions.md`。

适用于 Paper/Spigot/Bukkit/Folia 插件开发，以及 Forge/Fabric 模组开发。

---

## 线程模型（铁律）

- **主线程**：World/Entity/Player/Block 操作 · 打开 GUI · 发数据包 · 绑定大多数 Bukkit API
- **异步**：数据库 · 网络 · 文件 IO；完成后必须 Scheduler 回主线程

### Folia 特殊规则

- 用实体/区域调度器，非全局调度器
- 不同区域的实体不能直接交互

---

## 配置文件

- 配置文件是给用户看和改的，须人类可读，注释充分
- **禁止**在 config.yml 内嵌不可编辑内容（序列化数据/Base64/二进制）
- 用户配置 vs 插件数据分离：配置 → config.yml · 数据 → data/*.yml 或数据库
- `<PluginName> reload` 指令必须有，一次性重载所有配置
- 所有指令须有 Tab 补全
- 本地配置文件仅为示例，不得与云端运行配置混淆
- 配置版本号，支持迁移
- 语言文件独立（lang/zh_CN.yml · lang/en_US.yml）

### 项目结构

```
resources/
├── plugin.yml          # 元数据（api-version 必须声明）
├── config.yml          # 用户配置
├── data/               # 插件内部数据（非用户编辑）
└── lang/               # 多语言（必须有）
    ├── zh_CN.yml
    └── en_US.yml
```

### plugin.yml 要点

- `api-version` 必须声明（否则兼容警告）
- `depend` vs `softdepend`：硬依赖 vs 软依赖，影响加载顺序
- 权限节点在此声明，非代码硬编码

---

## GUI 系统

- `InventoryClickEvent` 必须 `setCancelled(true)`，否则物品被拿走
- 区分点击类型：左键/右键/Shift/数字键/拖拽
- 处理 `InventoryCloseEvent`（玩家可随时关闭）
- **异步打开 GUI 会崩服**：须主线程 `player.openInventory()`
- 插件关闭/重载时须处理 GUI 存活周期
- 物品比对：用 `ItemStack.isSimilar()` 或自定义 NBT，不用 `==`
- 用 PersistentDataContainer/NBT 标识 GUI 物品，非名称/Lore
- GUI Holder 模式：自定义 InventoryHolder 区分不同 GUI
- 分页 GUI 注意边界检查；动态更新用 `setItem()` 非重新打开
- 槽位 Index 从 0 开始，不得 -1

---

## 事件系统

| 优先级 | 场景 |
|--------|------|
| LOWEST | 最先处理、可能取消 |
| LOW | 保护类插件（领地/权限） |
| NORMAL | 常规功能（默认） |
| HIGH | 保护插件之后处理 |
| HIGHEST | 最终决定权 |
| MONITOR | 仅记录/统计，**禁止修改** |

- `ignoreCancelled = true`：忽略已取消事件
- 高频事件（Move/Physics）须轻量，禁止 IO/DB
- `PlayerJoinEvent` 时玩家可能未完全加载，需延迟 1 tick
- 命令执行区分：玩家/控制台/命令方块
- Tab 补全返回空列表而非 null；异步命令结果须回主线程

---

## 数据持久化

| 方案 | 场景 | 注意 |
|------|------|------|
| YAML/JSON | 少量配置 | 不适合频繁写入 |
| SQLite | 中等数据 | 单服适用 |
| MySQL | 大数据/多服 | 须连接池 |

### 操作原则

- 读写必须异步
- 玩家数据：加入时加载，退出时保存，定时自动保存
- 关服时同步保存所有数据

### 多服架构要点

- 连接池：`核心数 * 2 + 1`，心跳检测防断连
- 版本号：共享数据加 `version` 字段防脏写
- 缓存同步：DB 改完广播清缓存，或版本号避免读旧值
- 幂等：`INSERT ... ON DUPLICATE KEY UPDATE`
- 事务隔离：经济数据 SERIALIZABLE，统计数据 READ COMMITTED
- 故障降级：连接失败用本地缓存标脏状态

### 跨服竞争态

| 问题 | 解法 |
|------|------|
| 读旧数据 | 版本号对比取最新 |
| 存储延迟 | 关键数据同步等待 |
| 并发修改 | 版本号 + Redis 全局锁 |
| 计算丢失 | 加计算锁或 DB 端处理 |

### DB 与内存交互

| 场景 | 策略 |
|------|------|
| DB 改 → 内存无感 | 广播通知清缓存 |
| 内存改 → DB 未同步 | 版本号判断 |
| 并发读写 | ConcurrentHashMap + 读写锁 |
| 缓存预热 | 「加载中」标志 |

### 常见陷阱

- `Bukkit.getPlayer()` 可能返回 null；下线后 Player 对象失效；用 UUID 非玩家名
- ItemStack 是可变对象须 clone；空气是 null 或 AIR；耐久/附魔/NBT 须考虑
- 区块未加载不能操作方块；跨世界传送检查世界存在；世界卸载清理数据

---

## NMS 与版本兼容

API 优先级：Bukkit API > Spigot API > Paper API > NMS

仅在 API 无法实现时用 NMS（数据包/底层操作/性能关键路径）

- NMS 代码放独立模块，适配器模式隔离
- 反射调用须完整异常处理
- 启动时版本检测，不支持则禁用功能而非崩溃
- 禁止兼容逻辑散落全项目
- 版本差异点显式隔离（adapter）
- Adventure API（Paper）优于传统 ChatColor

### 常见兼容问题

- 物品 NBT API 变化（1.20.5+ DataComponents）
- 命令系统变化（Brigadier）
- 文本组件变化（Adventure）

---

## 自动化测试（零妥协）

**铁律**：任何功能须附带 `mvn test` 可运行的自动化测试。禁止「手动进服验证」替代。

详细测试规范（技术栈/基类/模式/排查）见：`references/testing.md`

### 验收标准

1. `mvn test` 零 Failures · 零 Errors · 零 Skipped
2. 每个公共 Service 方法：≥1 正常 + ≥1 异常测试
3. 金币/物品操作须验证「扣除-返还」对称性
4. DB 操作须用内存 SQLite 验证读写一致性
5. 禁止 `@Disabled` 跳过失败测试
