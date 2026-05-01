---
description: Development environment for AI agents.
applyTo: "**"
---
# AI 开发环境说明

默认 shell：macOS zsh/bash。裸命令优先；命令不存在时先探测 PATH 和项目文档，不假设原作者本机私有工具目录存在。

## 平台约定

- Home 目录：`$HOME` / `~`
- 路径风格：POSIX 路径，例如 `~/project`、`./src`、`/usr/local/bin`
- 脚本优先级：`.sh`、Python、Node.js；不要默认生成非 POSIX 脚本
- 多命令执行：优先拆成独立命令；确需串接时遵循 POSIX shell 语义
- 不写入 Token / 密码等 secrets 到脚本默认值或文档示例

## 运行时 / 构建

按项目实际信号文件和本机 PATH 探测工具，不假设固定版本或绝对安装目录：

- Python：`python3` / `pip3` / `uv`
- Node.js：`node` / `npm` / `pnpm` / `yarn` / `bun`
- Java：`java` / `javac` / `mvn` / `gradle`
- Go：`go`
- Rust：`cargo` / `rustc`
- .NET：`dotnet`
- C/C++：`clang` / `gcc` / `cmake`

## 数据库客户端

不要假设本机固定账号密码。根据项目 `.env.example`、compose 文件、README 或迁移配置确认 `mysql`、`psql`、`redis-cli`、`sqlite3` 等工具。

## 浏览器自动化

GUI / 浏览器自动化启动前记录 PID、端口或会话标识；任务结束时关闭本次启动的资源。

