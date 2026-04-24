---
description: Development environment for AI agents.
applyTo: "**"
---
# AI 开发环境说明

默认 shell：pwsh。裸命令优先。shell 不认命令时先执行：

环境变量（User）：
- JAVA_HOME = F:\Runtimes\Java\Jdk17（默认 JDK17；JDK21 也可用）
- HTTP(S)_PROXY = http://127.0.0.1:7897
- CLOUDFLARE_GLOBAL_KEY = <User 作用域已配置，账号级全权限，AI 可随意操作 Cloudflare>
- CLOUDFLARE_EMAIL = dragonbaimo@gmail.com

## 运行时 / 构建（自动拿最新版，无需锁版本）

- java javac jar jps — JDK17 17.0.12（F:\Runtimes\Java\Jdk17\bin）
- java21 — JDK21 21.0.10（F:\Runtimes\Java\Jdk21\bin，需要时显式 & 'F:\Runtimes\Java\Jdk21\bin\java.exe' 或切 JAVA_HOME）
- mvn — Maven 3.9.9（F:\BuildTools\Maven\apache-maven-3.9.9\bin）
- gradle — Gradle launcher（F:\BuildTools\Gradle）
- python pip — Python 3.10.11（F:\Runtimes\Python\Python310）
- uv — 0.8.0（F:\EnvManagers\Python\uv\uv-0.8.0）
- conda — 25.3.1（F:\EnvManagers\Python\Miniconda）
- node npm — Node 22.22.2 / npm 10.9.7（F:\Runtimes\NodeJS\node-v22.22.2-win-x64）
- pnpm — 10.8.1（npm 全局，F:\EnvManagers\JavaScript\npm-global）
- bun — 1.2.11（F:\Runtimes\Bun\bun-1.2.11\bin）
- go — 1.25.5（F:\Runtimes\Go\go1.25.5\bin）
- cargo rustc — Rust 1.86.0（F:\Runtimes\Rust）
- gcc g++ — MinGW 14.2.0（F:\BuildTools\MinGW\bin）
- clang — 20.1.4（F:\BuildTools\LLVM\llvm-20.1.4\bin）
- cmake — 4.0.1（F:\BuildTools\CMake\cmake-4.0.1\bin）
- dotnet — 10.0.107（系统自带）
- Rscript — R 4.5.1（F:\Runtimes\R\R-4.5.1\bin）

## 版本控制与平台 CLI

- git — 2.48.0（F:\VCS\Git\Git-2.48.0.rc2.windows.1\bin）
- gh — GitHub 官方 CLI：仓库/Issue/PR/Release/Actions。已登录（F:\VCS\GitHubCLI\gh-2.75.0）
- glab — GitLab 官方 CLI：同 gh 对应 GitLab 能力。已登录（F:\VCS\GitLabCLI\glab-1.81.0\bin）
- vercel — Vercel 部署 CLI：deploy、env、logs、dns。已登录（npm 全局）
- wrangler — Cloudflare Workers/Pages/KV/D1/R2 部署管理，4.84.1（npm 全局）
- supabase — Supabase 项目管理、数据库迁移、Edge Functions，2.90.0（F:\Tools\SupabaseCLI\supabase-2.90.0）
- stripe — Stripe 事件监听、webhook 转发、测试支付流，1.40.7（F:\Tools\StripeCLI\stripe-1.40.7）。已登录（沙盒：广州知行云智科创有限公司，acct_1TPY4KHxFu0t0gCz）
- cloudflared — Cloudflare Tunnel 客户端，2026.3.0（F:\Tools\Cloudflare\cloudflared）
- cf-dns — Cloudflare DNS 本地包装脚本：list/get/upsert/delete（F:\Tools\Cloudflare\cf-dns.cmd）
- cf.py — Cloudflare 全自动管理 Python 脚本：DNS / Email Routing / Workers / Resend（F:\Tools\Cloudflare\cf.py，走 Global Key，AI 授权全开）

## 数据库客户端

- mysql — 8.0.43（F:\Databases\MySQL\mysql-8.0.43-winx64\bin），连接 127.0.0.1:3306 root/root
- psql — PostgreSQL 16.9（F:\Databases\PostgreSQL\engine\pgsql\bin），连接 127.0.0.1:5432 postgres/root 或 root/root
- redis-cli — Redis 客户端（F:\Databases\Redis\redis），连接 127.0.0.1:6379 无密码

## Windows / 浏览器自动化

- windows-use — Windows 桌面 GUI 自动化 CLI，由 LLM 驱动鼠标/键盘/窗口（F:\EnvManagers\Python\uv-tools\bin）
- patchright — Patchright（抗指纹 Playwright fork）浏览器自动化，1.58.2；浏览器资产在 PLAYWRIGHT_BROWSERS_PATH（F:\EnvManagers\Python\uv-tools\bin）

## 其他

- adb sdkmanager emulator — Android SDK 1.0.41（F:\Mobile\Android\sdk）
- ffmpeg — 7.1.1（F:\chocolatey\bin）
- dot — Graphviz 14.0.0（F:\Tools\Graphviz\Graphviz-14.0.0-win64\bin）
- proguard — Java 代码混淆 7.6.1（F:\BuildTools\ProGuard\proguard-7.6.1\bin）
- fzf — 0.70.0（F:\Tools\Fzf\fzf-0.70.0）
- ollama — 本地 LLM 运行时 0.21.0（F:\Tools\Ollama\ollama-0.20.5）
- code — VS Code 1.116.0（D:\ProgramCategories\Microsoft VS Code\bin）
- pwsh dotnet winget wsl — 系统自带

## Cloudflare（AI 已授权全操作）

Global Key 已配置（`CLOUDFLARE_GLOBAL_KEY`），覆盖账号所有能力，无需再问授权。

- `python F:\Tools\Cloudflare\cf.py status` — 查看用法与当前权限
- `cf-dns list` — 快速列 DNS（PowerShell 包装，仅 DNS）

## uv 工具约定

- 安装目录：F:\EnvManagers\Python\uv-tools\tools；bin：F:\EnvManagers\Python\uv-tools\bin
- Python 3.13 托管运行时：F:\Runtimes\Python\uv-managed\cpython-3.13.5-windows-x86_64-none（作为 uv tool install --python 的显式目标）
- 新 shell 必须继承 UV_TOOL_DIR / UV_TOOL_BIN_DIR / PLAYWRIGHT_BROWSERS_PATH

## 注意

- 默认 JDK17；需要 JDK21 时显式走 F:\Runtimes\Java\Jdk21\bin\java.exe 或切 JAVA_HOME
- 不写入 Token / 密码等 secrets 到脚本默认值或文档示例
- 不手工移动 Windows Kits、Visual Studio、chocolatey、Application Verifier、WSL