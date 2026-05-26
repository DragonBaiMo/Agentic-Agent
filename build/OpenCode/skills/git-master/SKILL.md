---
name: git-master
description: >
  Git workflow guidance for macOS: inspect history, manage branches,
  review changes, resolve conflicts, and keep commits intentional.
---

# Git Master

默认 shell：zsh/bash。

## 基本原则

- 修改前先看 `git status --short --branch`
- 提交前用 `git diff` 和 `git diff --staged` 审查
- 不重置或覆盖用户未确认的改动
- 处理冲突时先理解双方变更，再决定保留、合并或重写

## 常用命令

```bash
git status --short --branch
git diff
git diff --staged
git log --oneline --decorate -n 20
git branch --show-current
```

## 提交

```bash
git add <paths>
git commit -m "type(scope): summary"
```

## 排查历史

```bash
git log --oneline -- <path>
git blame -- <path>
git show <commit>
```

