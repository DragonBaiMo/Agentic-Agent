---
name: one-click-scripts
description: >
  为任意项目生成「一键启动」和「一键重置/重导入」的 Windows BAT 脚本。
  自动识别技术栈（Python/Node.js/Java/Go/.NET 等），生成含中文输出、双击即运行的 .bat 文件。
  覆盖：环境创建、依赖安装、编译（如需）、服务启动、数据库清空重建、端口冲突处理。
  触发词："一键启动"、"生成启动脚本"、"一键导入"、"一键重置"、"生成重置脚本"、"双击启动"、
  "写个 start.bat"、"写个启动脚本"、"bat 脚本"、"一键部署"。
  不适用于：Linux/macOS shell 脚本（仅 Windows BAT）、Docker compose、CI/CD pipeline。
---

# One-Click Scripts —— 一键脚本生成

为项目生成三个可双击运行的 `.bat` 脚本，职责分离：

| 脚本 | 职责 | 运行频率 |
|------|------|---------|
| `reimport.bat` | 清空数据库 → 重新初始化导入 | 偶尔（数据重置时） |
| `setup.bat` | 创建环境 → 安装依赖 → 编译（如需） | 一次（首次部署 / 环境损坏时） |
| `start.bat` | 启动服务（假设环境已就绪） | 频繁（每次启动） |

---

## 固定约束

- 输出格式：`.bat`（Windows 批处理），不生成 `.ps1` / `.sh`
- 编码：所有脚本第二行必须是 `chcp 65001 >nul`
- 文件编码：必须保存为 `UTF-8 无 BOM`（禁止 UTF-8 BOM）
- 行尾：必须使用 `CRLF`（禁止仅 LF）
- 路径：用 `%~dp0` 获取脚本所在目录，所有路径由此拼接，禁止硬编码绝对路径
- 错误处理：每个关键步骤后 `if errorlevel 1` 检查，失败时立即 `exit /b 1`；仅 `reimport.bat` 的危险确认步骤允许显式等待用户输入
- 启动器行为：`start.bat` 成功拉起服务后必须自行退出，禁止在成功路径上生成 `pause`、`Press any key to continue` 或要求用户额外确认
- 多服务启动：前后端或多进程项目，优先生成服务级子脚本（如 `start-frontend.bat`、`start-backend.bat`），再由根 `start.bat` 负责并行拉起这些子脚本并退出
- 中文：所有 echo 输出使用中文

### 批处理陷阱（必须规避）

1. **BOM 陷阱**：UTF-8 BOM 会导致首行变成 `锘緻echo`，脚本整体错位解析。
2. **行尾陷阱**：仅 LF 行尾会让 `cmd` 出现首字符丢失（如 `echo` 变 `cho`、`npm` 变 `m`）。
3. **引号陷阱**：`start ... cmd /k "...cd /d "%ROOT%..."..."` 若未双引号转义，会把后半段切断。

### 强制自检（生成后必须执行）

- 自检 1：文件头不能是 `EF BB BF`（有则说明 BOM 错误）
- 自检 2：文件内换行应包含 `0D 0A`（CRLF）
- 自检 3：`start` 命令内路径需写成 `""%ROOT%...""` 双引号嵌套

---

## 主流程

### Step 1：项目探测

扫描项目根目录，确定以下信息。**每一项都必须落实到具体值，不能留空。**

#### 1.1 技术栈组成

检查信号文件确定后端/前端技术栈：

| 信号文件 | 技术栈 | 运行时要求 |
|---------|--------|-----------|
| `requirements.txt` / `pyproject.toml` / `Pipfile` | Python | `python` ≥ 3.x |
| `package.json` | Node.js | `node` + `npm`/`pnpm`/`yarn` |
| `pom.xml` | Java Maven | `java` + `mvn` |
| `build.gradle` / `build.gradle.kts` | Java/Kotlin Gradle | `java` + `gradle` |
| `go.mod` | Go | `go` |
| `Cargo.toml` | Rust | `cargo` |
| `*.sln` / `*.csproj` | .NET | `dotnet` |
| `composer.json` | PHP | `php` + `composer` |

#### 1.2 目录结构

是否前后端分离（如 `backend/` + `frontend/`），还是单体。

#### 1.3 数据库凭据发现（关键）

**必须找到数据库名称、路径（或连接串）、默认用户名密码。** 按以下优先级搜索：

| 搜索位置 | 要找什么 | 示例 |
|---------|---------|------|
| `config.py` / `settings.py` / `application.yml` / `application.properties` / `.env` | 数据库名称、路径、连接串 | `DATABASE_PATH = 'freshlite.db'`、`spring.datasource.url=jdbc:mysql://...` |
| `init_db.py` / `seed.py` / `*.sql` / `migrations/` | 初始化脚本、默认用户创建语句 | `INSERT INTO t_user ... ('admin', 'admin123')` |
| `docker-compose.yml` | 数据库容器环境变量 | `MYSQL_ROOT_PASSWORD: root123` |
| `config/*.json` / `database.json` | 连接配置 | `"host": "localhost", "database": "mydb"` |

**搜索策略：**
1. 先用 `grep` 搜索关键词：`DATABASE`、`DB_`、`SQLALCHEMY`、`datasource`、`mongodb`、`redis`、`sqlite`、`.db`、`.sqlite3`、`password`、`passwd`
2. 读取配置文件中的数据库路径/名称
3. 在 init 脚本中搜索 `INSERT INTO.*user`、`password_hash`、`generate_password_hash` 找默认账号
4. 如果找不到 → **必须询问用户**

**产出要求：**
- 数据库类型：SQLite / MySQL / PostgreSQL / MongoDB / 其他
- 数据库文件路径（SQLite）或连接串（SQL 数据库）
- 初始化脚本路径
- 默认管理员账号和密码（明文，用于显示在脚本输出中）

#### 1.4 依赖安装要求发现

**必须确定每种技术栈需要安装什么、用什么命令安装。**

| 技术栈 | 依赖清单来源 | 安装命令 | 安装完成检测 |
|--------|-------------|---------|-------------|
| Python | `requirements.txt` / `pyproject.toml` / `Pipfile` | `pip install -r requirements.txt` | `import flask`（用主框架包名检测） |
| Node.js | `package.json` + 锁文件 | `npm install` / `pnpm install` / `yarn` | `node_modules/` 目录存在 |
| Java Maven | `pom.xml` | `mvn install -DskipTests` | `target/` 目录存在 |
| Java Gradle | `build.gradle` | `gradlew build -x test` | `build/libs/` 目录存在 |
| Go | `go.mod` | `go mod download` | `go build` 成功 |
| .NET | `*.csproj` | `dotnet restore` | `bin/` 目录存在 |

**Python 特殊处理：**
1. 检查是否需要虚拟环境（大多数情况需要）
2. 确定 venv 路径（通常 `.venv` 或 `venv`）— 搜索项目中已有的 venv 目录
3. 确定 `requirements.txt` 的位置（可能在根目录或子目录如 `backend/`）
4. 确定标记包名（用于 `import xxx` 快速检测依赖是否已装）— 读取 requirements.txt 第一个核心包

**Node.js 特殊处理：**
1. 检测包管理器：`pnpm-lock.yaml` → pnpm、`yarn.lock` → yarn、其他 → npm
2. 检测是否需要编译：`tsconfig.json` 存在 + `vite.config.*` / `webpack.config.*`

#### 1.5 入口文件

启动脚本（`run_*.py`、`main.py`、`app.py`、`manage.py`、`server.js`、`index.js`）和初始化脚本（`init_db.py`、`seed.py`、SQL 文件）。

#### 1.6 现有脚本

是否已有 `start.bat`、`setup.bat`、`reimport.bat` 等（避免覆盖，先读取理解）。

#### 1.7 端口号

从配置文件或启动脚本中搜索：`port`、`PORT`、`5000`、`3000`、`8080` 等。

当需要各技术栈的具体命令模式时，读取 `references/tech-patterns.md`。

**产出：** 一份完整项目概况，所有项都有具体值。

---

### Step 2：确认需求

向用户确认以下关键决策（仅在信息不充分时询问，能从代码推断的直接采用）：

| 决策点 | 默认值 | 何时询问 |
|--------|--------|---------|
| 启动模式 | 开发模式（dev） | 用户提到"部署"或"生产" |
| 前端是否编译 | dev 模式不编译 | 用户提到"打包"或"build" |
| 数据库重置是否保留用户数据 | 全部清空 | 检测到用户表有自定义数据 |
| 已有同名脚本的处理 | 覆盖 | 已有脚本内容复杂时 |
| 默认账号密码 | 从 init 脚本中提取 | 找不到默认账号时 |
| 数据库连接信息 | 从配置文件自动提取 | Step 1.3 搜索全部失败时 |
| 运行时版本要求 | 从配置/锁文件提取 | 项目未声明最低版本时 |

如果项目结构清晰、意图明确，跳过询问直接生成。

**产出：** 确认的需求参数。

---

### Step 3：生成 reimport.bat（一键导入数据库）

**职责**：清空数据库 → 重新执行初始化/导入脚本。不处理环境和依赖。

按以下段落顺序组装：

```
1. 文件头（@echo off + chcp 65001 + setlocal + 变量定义）
2. Banner + 警告（"此操作将清空所有数据！"）
3. 环境前置检查（虚拟环境/运行时是否存在 — 不存在则提示先运行 setup.bat）
4. 用户确认（set /p confirm="确认操作？(Y/N): "）
5. 关闭相关服务进程（精准杀死，按端口号或窗口标题定位）
6. 删除数据库文件（SQLite）/ 执行 DROP 脚本（MySQL/PG）
7. 清理衍生文件（模型文件、缓存、日志等，如有）
8. 重新执行初始化脚本（init_db.py / SQL seed 等）
9. 输出结果摘要（导入了多少数据、默认账号密码）
10. 输出完成摘要；若需要避免窗口闪退，仅此脚本允许在成功路径末尾保留 `pause`
```

**关键实现细节：**

- 确认步骤：**必须有**，防止误操作
- 进程关闭：用端口号精准定位（`netstat -aon | findstr ":PORT " | findstr "LISTENING"`），不用 `taskkill /IM python.exe /F`
- SQLite：直接 `del` 数据库文件 → 重新跑 init 脚本
- SQL 数据库：执行 DROP 脚本 → DDL → Seed
- 前置检查：虚拟环境不存在时提示"请先运行 setup.bat"并退出

**产出：** `reimport.bat` 文件。

---

### Step 4：生成 setup.bat（一键环境搭建）

**职责**：创建运行环境 → 安装所有依赖 → 编译（如需）。不启动服务，不初始化数据库。

按以下段落顺序组装：

```
1. 文件头
2. Banner（"环境搭建"）
3. 运行时检测（python --version / node -v / java -version — 不存在则报错退出）
4. 后端环境创建（创建 venv / 无需创建则跳过）
5. 后端依赖安装（pip install / mvn install / go mod download 等）
6. 前端依赖安装（npm install / pnpm install / yarn install）
7. 编译步骤（TypeScript build / Maven package / Gradle build / Go build — 仅需要编译的技术栈）
8. 数据库初始化（if not exist db then init — 首次自动初始化）
9. 完成摘要（列出已完成的步骤）
10. 输出完成摘要；若需要避免窗口闪退，可在此脚本成功路径末尾保留 `pause`
```

**关键实现细节：**

- 幂等性：每个步骤先检查是否已完成，已完成则跳过（`if exist venv` / `if exist node_modules`）
- 连续运行两次不报错
- 依赖安装检查：Python 用标记包 `import` 检测；Node.js 用 `node_modules` 存在性
- 编译检查：检测产物是否存在（`target/*.jar` / `build/libs/*.jar` / `dist/`）
- 数据库初始化放在最后：环境就绪后才能初始化

**产出：** `setup.bat` 文件。

---

### Step 5：生成 start.bat（一键启动）

**职责**：启动服务。假设环境已就绪（`setup.bat` 已运行过）。

**默认生成策略**：

- 根 `start.bat` 只做编排：前置检查、释放端口、输出地址、拉起子脚本、可选健康检查，然后立刻退出
- 多服务项目必须优先拆出服务级子脚本，例如 `start-frontend.bat`、`start-backend.bat`
- 子脚本负责在各自窗口执行长驻命令；根 `start.bat` 不直接前台跑后端，不承担日志驻留职责
- `start.bat` 成功路径禁止 `pause`，禁止出现 `Press any key to continue`

按以下段落顺序组装：

```
1. 文件头
2. Banner（"启动服务"）
3. 前置检查（虚拟环境/依赖是否存在 — 不存在则提示先运行 setup.bat）
4. 数据库检查（不存在则提示先运行 reimport.bat 或自动调用 init）
5. 端口冲突检测与清理
6. 输出访问地址 + 默认账号密码
7. 启动服务级子脚本（用 start 命令分别启动 `start-frontend.bat`、`start-backend.bat` 等）
8. 可选健康检查 / 就绪等待
9. 输出结果摘要并 `exit /b 0`
```

**关键实现细节：**

- **不安装依赖、不创建环境** — 这是 `setup.bat` 的事
- 前置检查失败时给出明确提示："请先双击 setup.bat 搭建环境"
- 多服务用 `start "窗口标题" "%~dp0start-xxx.bat"` 或 `start "窗口标题" cmd /k "call start-xxx.bat"` 拉起子脚本
- 根 `start.bat` 只作为启动器存在，成功后立即退出，不保留当前窗口
- 长驻日志应出现在子脚本对应的新窗口里，而不是主启动器窗口里
- 数据库不存在时可选择自动初始化或提示运行 `reimport.bat`

**产出：** `start.bat` 文件。

---

### Step 6：验证

1. **语法检查**：确认所有变量引用正确（`%VAR%` 配对）、路径转义正确
2. **路径验证**：确认脚本中引用的所有文件路径在项目中实际存在
3. **幂等性**：`setup.bat` 连续运行两次不报错（已存在的环境/依赖跳过）
4. **职责边界**：`start.bat` 不安装依赖；`reimport.bat` 不创建环境；`setup.bat` 不启动服务
5. **跨脚本引用**：`start.bat` 和 `reimport.bat` 的前置检查提示与 `setup.bat` 名称一致
6. **错误恢复**：关键步骤失败时脚本中断并给出可读的中文错误提示
7. **编码验证**：确认脚本为 UTF-8 无 BOM
8. **行尾验证**：确认脚本为 CRLF，不是 LF
9. **冒烟执行**：`cmd /c start.bat` 首屏无 `锘緻echo`、无 `...不是内部或外部命令`
10. **启动器行为验证**：`start.bat` 成功后不出现 `Press any key to continue`，且主窗口自动结束；长驻日志仅存在于子脚本窗口

**产出：** 三个验证通过的脚本文件。

---

### Step 7：输出交付

向用户说明：

```
首次使用：
  1. 双击 setup.bat  → 搭建环境（创建虚拟环境、安装依赖、初始化数据库）
  2. 双击 start.bat  → 启动服务

日常使用：
  双击 start.bat → 直接启动

需要重置数据时：
  双击 reimport.bat → 清空数据库并重新导入

默认账号：xxx / xxx
```

---

## 失败处理

| 场景 | 应对 |
|------|------|
| 无法识别技术栈 | 询问用户项目使用什么语言/框架 |
| 入口文件不明确 | 列出候选文件，让用户选择 |
| 项目结构非标准 | 询问启动命令和初始化命令 |
| 已有脚本与需求冲突 | 展示已有脚本内容，询问是覆盖还是重命名 |
| BAT 语法在特定 Windows 版本不兼容 | 使用最保守的语法子集（cmd.exe 兼容） |

---

## 禁止事项

- **禁止**生成 `taskkill /IM python.exe /F` 等一刀切杀进程命令
- **禁止**硬编码绝对路径（如 `C:\Users\xxx\project`）
- **禁止**省略 `chcp 65001`（中文乱码）
- **禁止**在 `start.bat` 成功路径中使用 `pause`、`set /p` 或任何导致 `Press any key to continue` 的等待语句
- **禁止**省略错误检查（`if errorlevel 1`）
- **禁止**在 `reimport.bat` 中省略用户确认步骤
- **禁止**使用 PowerShell 特有语法（如 `&&`、管道对象）
- **禁止**输出英文 echo（全部中文）
- **禁止**在 `start.bat` 中安装依赖或创建环境（职责属于 `setup.bat`）
- **禁止**在 `reimport.bat` 中创建虚拟环境或安装依赖（职责属于 `setup.bat`）
- **禁止**让根 `start.bat` 直接承载后端前台常驻进程；多服务项目必须拆成子脚本或独立窗口命令

---

## References 导航

| 文件 | 触发条件 |
|------|---------|
| `references/tech-patterns.md` | 需要特定技术栈的环境创建/依赖安装/编译/启动命令模式时 |
