# 技术栈识别与脚本模式

本文档提供各主流技术栈的环境检测、依赖安装、编译、启动、数据库重置的标准命令模式。

---

## 1. 技术栈识别信号

按文件存在性判断项目技术栈：

| 信号文件 | 技术栈 | 运行时 |
|---------|--------|--------|
| `requirements.txt` / `pyproject.toml` / `setup.py` / `Pipfile` | Python | `python` / `python3` |
| `package.json` | Node.js | `node` / `npm` / `pnpm` / `yarn` |
| `pom.xml` | Java (Maven) | `java` / `mvn` |
| `build.gradle` / `build.gradle.kts` | Java/Kotlin (Gradle) | `java` / `gradle` |
| `go.mod` | Go | `go` |
| `Cargo.toml` | Rust | `cargo` |
| `*.sln` / `*.csproj` | .NET / C# | `dotnet` |
| `composer.json` | PHP | `php` / `composer` |

多个信号共存时，判断为多模块项目（如前后端分离），需为每个模块生成对应段落。

---

## 2. Python 模式

### 环境探测与创建

```bat
@rem 检查 venv 是否存在
if not exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    echo [INFO] 创建 Python 虚拟环境...
    python -m venv "%PROJECT_DIR%\.venv"
    if errorlevel 1 (
        echo [ERROR] 虚拟环境创建失败，请确认 Python 已安装
        pause & exit /b 1
    )
)
set "PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "PIP=%PROJECT_DIR%\.venv\Scripts\pip.exe"
```

### 依赖安装

```bat
@rem 检查依赖是否已安装（用 flask 作为标记包示例）
"%PYTHON%" -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 Python 依赖...
    "%PIP%" install -r "%PROJECT_DIR%\requirements.txt" -q
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        pause & exit /b 1
    )
)
```

### 数据库初始化

```bat
@rem SQLite 示例
if not exist "%DB_PATH%" (
    echo [INFO] 初始化数据库...
    "%PYTHON%" "%INIT_SCRIPT%"
)
```

### 启动

```bat
echo [INFO] 启动后端服务...
start "Backend" cmd /c ""%PYTHON%" "%RUN_SCRIPT%""
```

### 数据库重置

```bat
echo [WARN] 即将删除数据库并重新导入...
if exist "%DB_PATH%" del /q "%DB_PATH%"
"%PYTHON%" "%INIT_SCRIPT%"
```

---

## 3. Node.js 模式

### 包管理器检测

```bat
@rem 检测包管理器
if exist "%PROJECT_DIR%\pnpm-lock.yaml" (
    set "PKG_MGR=pnpm"
) else if exist "%PROJECT_DIR%\yarn.lock" (
    set "PKG_MGR=yarn"
) else (
    set "PKG_MGR=npm"
)
```

### 依赖安装

```bat
if not exist "%PROJECT_DIR%\node_modules" (
    echo [INFO] 安装 Node.js 依赖...
    cd /d "%PROJECT_DIR%"
    %PKG_MGR% install
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        pause & exit /b 1
    )
)
```

### 编译（TypeScript / Vite build）

```bat
@rem 仅生产部署时需要编译；dev 模式下 Vite/webpack 自带热更新
@rem 检测是否需要编译
if exist "%PROJECT_DIR%\tsconfig.json" (
    echo [INFO] 编译 TypeScript...
    cd /d "%PROJECT_DIR%"
    %PKG_MGR% run build
)
```

### 启动

```bat
@rem 开发模式
start "Frontend" cmd /c "cd /d "%PROJECT_DIR%" && %PKG_MGR% run dev"
@rem 或生产模式
start "Frontend" cmd /c "cd /d "%PROJECT_DIR%" && %PKG_MGR% run start"
```

---

## 4. Java (Maven) 模式

### 编译与打包

```bat
if not exist "%PROJECT_DIR%\target\*.jar" (
    echo [INFO] 编译 Java 项目...
    cd /d "%PROJECT_DIR%"
    mvn package -DskipTests -q
    if errorlevel 1 (
        echo [ERROR] Maven 编译失败
        pause & exit /b 1
    )
)
```

### 启动

```bat
for %%f in ("%PROJECT_DIR%\target\*.jar") do (
    start "Backend" cmd /c "java -jar "%%f""
    goto :java_started
)
:java_started
```

---

## 5. Java (Gradle) 模式

### 编译

```bat
if not exist "%PROJECT_DIR%\build\libs\*.jar" (
    echo [INFO] 编译项目...
    cd /d "%PROJECT_DIR%"
    gradlew.bat build -x test -q
)
```

### 启动

```bat
for %%f in ("%PROJECT_DIR%\build\libs\*.jar") do (
    start "Backend" cmd /c "java -jar "%%f""
    goto :gradle_started
)
:gradle_started
```

---

## 6. Go 模式

### 编译

```bat
echo [INFO] 编译 Go 项目...
cd /d "%PROJECT_DIR%"
go build -o "%PROJECT_DIR%\app.exe" .
```

### 启动

```bat
start "Backend" cmd /c ""%PROJECT_DIR%\app.exe""
```

---

## 7. .NET 模式

### 编译

```bat
echo [INFO] 编译 .NET 项目...
cd /d "%PROJECT_DIR%"
dotnet build --configuration Release -q
```

### 启动

```bat
start "Backend" cmd /c "cd /d "%PROJECT_DIR%" && dotnet run --configuration Release"
```

---

## 8. 数据库重置通用模式

### SQLite

```bat
if exist "%DB_PATH%" del /q "%DB_PATH%"
"%INIT_CMD%"
```

### MySQL / PostgreSQL / SQL Server

```bat
@rem 执行 DROP + 重建脚本
echo [INFO] 重置数据库...
"%DB_CLIENT%" -u %DB_USER% -p%DB_PASS% -h %DB_HOST% < "%SQL_DIR%\drop_all.sql"
"%DB_CLIENT%" -u %DB_USER% -p%DB_PASS% -h %DB_HOST% < "%SQL_DIR%\ddl.sql"
"%DB_CLIENT%" -u %DB_USER% -p%DB_PASS% -h %DB_HOST% < "%SQL_DIR%\seed.sql"
```

---

## 9. 端口冲突处理模式

```bat
@rem 检测端口是否被占用
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo [WARN] 端口 %PORT% 被 PID %%a 占用，正在关闭...
    taskkill /PID %%a /F >nul 2>&1
)
```

---

## 10. 通用 BAT 骨架

### 三脚本通用头部

所有生成的 BAT 文件必须包含以下头部：

```bat
@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"
```

### 编码与行尾（强制）

- 文件编码：`UTF-8 无 BOM`
- 行尾：`CRLF`
- 不满足时常见报错：`锘緻echo 不是内部或外部命令`、`cho/m 不是内部或外部命令`

### `start` 引号安全模板（强制复用）

```bat
@rem 正确：路径中的引号要双写
start "Frontend" cmd /k "chcp 65001 >nul && cd /d ""%ROOT%frontend"" && npm run dev"

@rem 错误：会截断命令，导致 npm 被解析成 m
@rem start "Frontend" cmd /k "chcp 65001 >nul && cd /d "%ROOT%frontend" && npm run dev"
```

### 生成后自检命令（PowerShell）

```powershell
# 1) 检查 BOM（应不包含 EF BB BF）
Format-Hex -Path .\start.bat | Select-Object -First 2

# 2) 检查是否 CRLF（字节中应看到 0D 0A）
Format-Hex -Path .\start.bat | Select-Object -First 4

# 3) 冒烟执行（首屏不能出现“不是内部或外部命令”）
cmd /c start.bat
```

### reimport.bat 骨架（一键导入数据库）

```bat
@rem ... 头部 ...
echo ========================================
echo   项目名称 - 一键导入数据库
echo   (清空数据库并重新初始化)
echo ========================================

@rem 前置检查：环境是否就绪
if not exist "后端环境路径" (
    echo [错误] 运行环境未搭建，请先双击 setup.bat
    pause & exit /b 1
)

@rem 用户确认
echo [警告] 此操作将清空数据库并重新导入所有数据！
set /p confirm="确认继续？(Y/N): "
if /i not "%confirm%"=="Y" ( echo [取消] 操作已取消 & pause & exit /b 0 )

@rem 关闭占用进程（按端口精准杀死）
@rem 删除数据库
@rem 清理衍生文件（模型/缓存）
@rem 重新初始化
@rem 输出摘要
pause
```

### setup.bat 骨架（一键环境搭建）

```bat
@rem ... 头部 ...
echo ========================================
echo   项目名称 - 一键环境搭建
echo ========================================

@rem 运行时检测（python/node/java）
@rem 创建虚拟环境 / 跳过已存在
@rem 安装后端依赖 / 跳过已安装
@rem 安装前端依赖 / 跳过已安装
@rem 编译（如需）/ 跳过已编译
@rem 首次数据库初始化（if not exist db）

echo.
echo [完成] 环境搭建完成，请双击 start.bat 启动服务
pause
```

### start.bat 骨架（一键启动）

```bat
@rem ... 头部 ...
echo ========================================
echo   项目名称 - 一键启动
echo ========================================

@rem 前置检查：环境是否就绪
if not exist "后端环境路径" (
    echo [错误] 运行环境未搭建，请先双击 setup.bat
    pause & exit /b 1
)

@rem 数据库检查（不存在则提示 reimport.bat 或自动初始化）
@rem 端口冲突检测
@rem 输出访问地址 + 默认账号
@rem 启动前端（新窗口）
@rem 启动后端（当前窗口，前台运行）
pause
```

必须满足：
- `chcp 65001` 在第二行（中文正确显示）
- `setlocal enabledelayedexpansion`（变量延迟展开）
- `%~dp0` 获取脚本所在目录（支持双击运行）
- 所有路径用 `%ROOT%` 拼接（不硬编码绝对路径）
- `errorlevel` 检错 + `pause & exit /b 1` 中断
- 最终 `pause` 保持窗口（用户看到输出）
