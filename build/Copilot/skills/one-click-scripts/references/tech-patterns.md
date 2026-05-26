# One-Click Scripts Tech Patterns

目标平台：macOS / POSIX shell。

## Python

- 创建环境：`python3 -m venv .venv`
- 安装依赖：`.venv/bin/pip install -r requirements.txt`
- 运行：`.venv/bin/python app.py`

## Node.js

- 优先按 lockfile 选择 `pnpm install`、`yarn install` 或 `npm install`
- 启动脚本优先读取 `package.json` 的 `scripts`

## 端口检查

- 检查端口：`lsof -ti :<port>`
- 只终止确认属于本项目的进程，禁止一刀切杀运行时进程。

