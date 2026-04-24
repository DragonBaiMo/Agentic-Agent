# Agentic Agent — 多平台 Agent/Skill 分发

单一事实源 → 每平台适配器 → 各自安装路径的一站式分发。

## 目录结构

```
Agentic Agent/
├── source/                     # 唯一事实源（Copilot 原生格式）
│   ├── agents/*.agent.md
│   └── skills/<name>/
├── adapters/                   # 平台适配器
│   ├── base.py                 # PlatformAdapter 抽象基类 + 源加载
│   ├── copilot/                # Copilot 直通适配器
│   └── codex/                  # Codex TOML 适配器
├── build/                      # 各平台生成产物（入库）
│   ├── Copilot/
│   └── Codex/
├── scripts/
│   ├── build.py                # source → build/<Platform>/
│   └── distribute.py           # build/ → 本机真实安装路径
└── docs/
    └── codex-reference.md
```

## 常用命令

```powershell
# 构建全部平台
python scripts/build.py

# 只构建 Codex
python scripts/build.py --target codex

# 预演分发（不写盘）
python scripts/distribute.py --dry-run

# 分发全部平台（默认先重建 build/）
python scripts/distribute.py

# 只分发 Copilot，不重建
python scripts/distribute.py --target copilot --no-build

# 合并模式（保留目的地其他文件）
python scripts/distribute.py --mode merge
```

## 安装路径（Windows 默认）

| 平台    | build 产物               | 分发目标                              |
|---------|--------------------------|---------------------------------------|
| Copilot | `build/Copilot/agents`   | `%USERPROFILE%\.copilot\agents`       |
| Copilot | `build/Copilot/skills`   | `%USERPROFILE%\.copilot\skills`       |
| Codex   | `build/Codex/.codex`     | `%USERPROFILE%\.codex`                |
| Codex   | `build/Codex/.agents`    | `%USERPROFILE%\.agents`               |

## 新增平台（Claude / WindSurf / ...）

1. `adapters/<name>/__init__.py` 实现 `PlatformAdapter` 子类：
   - `name`, `display_name`
   - `build(source, out_root) -> BuildReport` — 写入平台原生格式
   - `install_targets()` — 返回 `InstallMapping(src_subpath, dst_path)`
2. 在 `adapters/__init__.py` 顶部 import 让其自动注册
3. 无需改动 `build.py` / `distribute.py`

每个适配器拥有自己独立的 formatter 逻辑，互不干扰。

## 源格式约定

- **Agent**：`source/agents/<name>.agent.md`，YAML frontmatter 必含 `description`；可选 `name`（不写则从文件名推断）
- **Skill**：`source/skills/<name>/SKILL.md` + 同目录任意资源（scripts/references/assets 等）

## 分发模式

- `replace`（默认）：目的地子目录被完全替换（先删再拷），确保与源一致
- `merge`：只覆盖同名文件，保留目的地其他内容

## 设计约束

- 一切面向 build 产物，不直接改真实安装路径
- 每次 build 幂等：目标目录先清再写
- 平台专有字段（如 Copilot 的 `tools` / `user-invocable`）由各自适配器决定保留/丢弃，不污染 source
