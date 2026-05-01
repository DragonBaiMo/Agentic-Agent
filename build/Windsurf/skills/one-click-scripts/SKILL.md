---
name: one-click-scripts
description: >
  为任意项目生成 POSIX shell 一键脚本，面向 macOS。
  自动识别技术栈，生成可从终端运行的 .sh 文件。
  触发词："一键启动"、"生成启动脚本"、"一键导入"、"一键重置"、"写个 start.sh"、"shell 脚本"。
---

# One-Click Scripts —— POSIX 一键脚本生成

目标平台：macOS。

为项目生成三个可运行的 `.sh` 脚本，职责分离：

| 脚本 | 职责 |
|------|------|
| `setup.sh` | 创建环境、安装依赖、必要时编译 |
| `start.sh` | 启动服务，假设环境已就绪 |
| `reimport.sh` | 清空数据库并重新初始化导入 |

## 固定约束

- 第一行使用 `#!/usr/bin/env bash`
- 使用 `set -euo pipefail`
- 文件编码 UTF-8，无 BOM，行尾 LF
- 生成后提示 `chmod +x setup.sh start.sh reimport.sh`
- 用脚本目录定位项目根，不硬编码绝对路径
- 危险数据操作必须二次确认
- `start.sh` 不安装依赖、不创建环境
- 多服务项目拆出服务级脚本，根脚本负责编排

