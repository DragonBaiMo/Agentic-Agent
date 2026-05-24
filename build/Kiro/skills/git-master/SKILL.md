---
name: git-master
description: "Git 工作流专家：原子提交、历史改写、代码考古、安全操作。处理 commit 拆分、rebase/squash、commit 风格检测、blame/bisect/pickaxe 搜索。触发词：commit、rebase、squash、blame、bisect、find commit、history、git 操作。"
argument-hint: "commit | rebase | squash | blame | bisect | find commit | history"
user-invocable: true
---

# Git Master

## 安全铁律（所有操作前置）

### 环境设置（防止交互式编辑器/分页器弹出）

每个 git 命令须确保不弹出交互编辑器：

```powershell
# 会话级设置（推荐）
$env:GIT_EDITOR = ":"; $env:EDITOR = ":"; $env:GIT_PAGER = "cat"

# 或单次命令内联
$env:GIT_EDITOR=":"; $env:EDITOR=":"; $env:GIT_PAGER="cat"; git <command>
```

```bash
# Bash/Linux
GIT_EDITOR=: EDITOR=: GIT_PAGER=cat git <command>
```

交互式 rebase 用 `GIT_SEQUENCE_EDITOR`：
```powershell
$env:GIT_SEQUENCE_EDITOR = ":"; git rebase -i HEAD~N
```

禁止调用：`vim` · `vi` · `nano` · `less` · `more` · `notepad`

### 提交/推送纪律

- **未经用户明确要求，绝不 commit**
- **未经用户明确要求，绝不 push**
- 禁止 `--no-verify` 跳过 pre-commit/pre-push 钩子
- 禁止修改已推送的 commit（除非用户明确指示）
- 提交前必须确认暂存内容：`git diff --staged --stat`

### 破坏性操作须确认

| 操作 | 风险 |
|------|------|
| `git branch -D` | 删除分支 |
| `git push --force` | 覆盖远程历史 |
| `git reset --hard` | 永久丢弃本地更改 |
| `git clean -fd` | 删除未跟踪文件/目录 |
| `git stash drop/clear` | 销毁暂存工作 |
| 修改已推送到共享分支的 commit | 改写公共历史 |

### 安全替代

| 危险操作 | 安全替代 |
|----------|----------|
| `git push --force` | `git push --force-with-lease` |
| `git reset --hard HEAD~1` | `git reset --soft HEAD~1`（保留更改在暂存区） |
| `git branch -D` | `git branch -d`（未合并时拒绝） |
| 修改已发布历史 | 创建 revert commit |

### PowerShell 命令串接

用 `;` 串接命令，禁止 `&&`：
```powershell
git add src/file.ts; git commit -m "feat: update file"
```

---

Three specializations activated by request pattern:

| Request Pattern | Mode |
|----------------|------|
| "commit", "stage", changes to record | `COMMIT` |
| "rebase", "squash", "cleanup", "fixup" | `REBASE` |
| "when was X added", "who wrote", "find commit", "blame" | `HISTORY` |

---

## COMMIT MODE

### Step 1 — Gather context (parallel)

```powershell
git status
git diff --staged --stat
git diff --stat
git log -30 --oneline
git branch --show-current
$base = git merge-base HEAD main 2>$null; if (-not $base) { git merge-base HEAD master }
git log --oneline "$base..HEAD"
```

### Step 2 — Detect commit style (MANDATORY OUTPUT)

Scan `git log -30` and classify:

| Style | Pattern | Example |
|-------|---------|---------|
| `SEMANTIC` | `type(scope): msg` | `feat: add login` |
| `PLAIN` | Plain description | `Add login feature` |
| `SHORT` | 1-3 words | `format`, `lint` |

Detection rule: count semantic-prefixed commits (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`, `ci:`, `perf:`). If >= 50% -> SEMANTIC. Else PLAIN. If most commits are 1-3 words -> SHORT.

Also detect language: if >= 50% Korean characters -> KOREAN, else ENGLISH.

**Print before proceeding:**
```
STYLE DETECTION
  Language: [ENGLISH|KOREAN]  — N/30 commits each
  Style: [SEMANTIC|PLAIN|SHORT]  — N/30 commits each
  Examples from log:
    1. "<actual message>"
    2. "<actual message>"
```

### Step 3 — Atomic split planning (MANDATORY OUTPUT)

**Hard rule: 3+ files MUST produce 2+ commits. No exceptions.**

Minimum commit count formula: `ceil(file_count / 3)`

Split by (priority order):
1. **Directory/module** — different dirs = different commits
2. **Concern** — UI vs logic vs config vs tests
3. **New vs modified** — additions separate from edits
4. **Dependency level** — types/constants first, then services, then controllers

Test pairing rule: test file ALWAYS commits with its implementation.
- `*.test.ts` with `*.ts`
- `*.spec.ts` with `*.ts`
- `test_*.py` with `*.py`

**Print before proceeding:**
```
COMMIT PLAN
  Files: N total  —  Minimum commits: ceil(N/3) = M  —  Planned: K

  COMMIT 1: "<message>"
    files/to/include.ts
    files/to/include.test.ts
    Why together: <one sentence>

  COMMIT 2: "<message>"
    other/file.ts
    Why together: <one sentence>

  Order: 1 -> 2 -> ... (dependency order)
```

For each commit with 3+ files, write a one-sentence justification. If you cannot, split.

Valid grouping reasons:
- "implementation + its direct test"
- "type definition + only consumer (would fail compilation without both)"
- "migration + model change (atomic schema update)"

Invalid reasons (must split):
- "all related to feature X"
- "changed at the same time"
- "makes sense together"

### Step 4 — Execute commits

```powershell
# For each commit group in dependency order:
git add <file1> <file2>
git diff --staged --stat          # verify staging
git commit -m "<message>"
git log -1 --oneline              # verify result
```

Message format by detected style:

| Style | Language | Format |
|-------|----------|--------|
| SEMANTIC | ENGLISH | `feat: add login button` |
| SEMANTIC | KOREAN | `feat: 로그인 버튼 추가` |
| PLAIN | ENGLISH | `Add login button` |
| PLAIN | KOREAN | `로그인 버튼 추가` |
| SHORT | any | `format` / `lint` / `타입 수정` |

### Step 5 — Verify

```powershell
git status                                            # must be clean
$base = git merge-base HEAD main 2>$null; if (-not $base) { git merge-base HEAD master }
git log --oneline "$base..HEAD"                       # review new history
```

**Automatic failure conditions:**
- 1 commit from 3+ unrelated files
- Test file in different commit from implementation
- Vague message like "Update files" or "Big refactor"
- Different modules merged into one commit without justification

---

## REBASE MODE

### Safety check first

```powershell
git branch --show-current
git log --oneline -20
git status --porcelain
git rev-parse --abbrev-ref "@{upstream}" 2>$null
```

Rules:
- On `main`/`master` -> ABORT, never rebase
- Dirty working tree -> stash first: `git stash push -m "pre-rebase"`
- Pushed commits -> force-push required; warn user
- All local commits -> safe for aggressive rewrites

### Autosquash (apply `fixup!` / `squash!` commits)

```powershell
$base = git merge-base HEAD main 2>$null; if (-not $base) { git merge-base HEAD master }
$env:GIT_SEQUENCE_EDITOR = ":"
git rebase -i --autosquash $base
Remove-Item Env:GIT_SEQUENCE_EDITOR
```

### Full squash (combine all branch commits into one)

```powershell
$base = git merge-base HEAD main 2>$null; if (-not $base) { git merge-base HEAD master }
git reset --soft $base
git commit -m "<combined message>"
```

### Rebase onto updated main

```powershell
git fetch origin
git rebase origin/main
```

### Conflict resolution workflow

```powershell
# Check what's conflicting
git status | Select-String "both modified"

# After editing conflicted file(s):
git add <resolved-file>
git rebase --continue

# Abort if stuck:
git rebase --abort
```

### Push after rebase

```powershell
# Never pushed before:
git push -u origin <branch>

# Already pushed (force-with-lease is mandatory, not --force):
git push --force-with-lease origin <branch>
```

### Post-rebase report

```
REBASE SUMMARY
  Strategy: <SQUASH|AUTOSQUASH|ONTO>
  Commits before: N  ->  after: M
  Conflicts resolved: K

HISTORY:
  <hash> <message>
  <hash> <message>
```

---

## HISTORY SEARCH MODE

### Determine search type

| Request | Tool | Command |
|---------|------|---------|
| "when was X added/removed" | Pickaxe | `git log -S` |
| "commits touching pattern" | Regex | `git log -G` |
| "who wrote this line" | Blame | `git blame` |
| "when did bug start" | Bisect | `git bisect` |
| "history of file" | File log | `git log -- path` |
| "find deleted code" | Pickaxe all branches | `git log -S --all` |

### Pickaxe (`git log -S`)

Finds commits where the count of a string changed (added or removed).

```powershell
# When was this string introduced?
git log -S "calculateDiscount" --oneline

# Show the actual diff:
git log -S "calculateDiscount" -p

# In a specific file:
git log -S "calculateDiscount" -- src/pricing.ts

# Across all branches (find deleted code):
git log -S "calculateDiscount" --all --oneline

# With date range:
git log -S "calculateDiscount" --since="2024-01-01" --oneline
```

### Regex search (`git log -G`)

Finds commits where the diff contains lines matching a pattern.

```powershell
# -S counts occurrences, -G matches diff lines — use -G for patterns
git log -G "def\s+my_function" --oneline
git log -G "TODO|FIXME" --oneline
git log -G "^import\s+requests" -- "*.py" --oneline
```

### Blame

```powershell
# Full file
git blame src/pricing.ts

# Specific line range
git blame -L 10,30 src/pricing.ts

# Ignore whitespace, follow moves/copies
git blame -wC src/pricing.ts
```

Reading output:
```
^abc1234 (Author 2024-01-15 10:30 +0900 42) code_here
          ------  ----------              --
          author  date                 line#
```

### Bisect (binary search for regression)

```powershell
git bisect start
git bisect bad                 # current commit is broken
git bisect good v1.0.0         # last known good tag or hash

# Git checks out midpoint. Test manually, then:
git bisect good   # this commit is fine
git bisect bad    # this commit has the bug

# Repeat until: "abc1234 is the first bad commit"
git bisect reset  # restore HEAD when done
```

Automated with a test script:
```powershell
git bisect start
git bisect bad HEAD
git bisect good v1.0.0
git bisect run <project-test-command> tests/regression.test.ts
# Exit 0 = good, 1-127 = bad, 125 = skip
```

### File history

```powershell
# Full history (follow renames)
git log --follow --oneline -- src/pricing.ts

# With diffs
git log -p -- src/pricing.ts

# Deleted files
git log --all --full-history -- "**/deleted-file.ts"

# Top contributors
git shortlog -sn -- src/pricing.ts
```

### Result format

```
SEARCH: "<query>"
COMMAND: git log -S "..." ...

RESULTS:
  abc1234  2024-06-15  feat: add discount calculation
  def5678  2024-05-20  refactor: extract pricing logic

MOST RELEVANT: abc1234
  Author: John Doe
  Date: 2024-06-15
  Summary: <what changed and why it matches>
```

---

## Quick Reference

**Style detection cheat sheet:**

| git log shows | Use |
|--------------|-----|
| `feat:`, `fix:`, `chore:` prefixes | SEMANTIC |
| `Add X`, `Fix Y`, `X 추가` | PLAIN |
| `format`, `lint`, `typo` | SHORT |

**Decision tree:**

```
On main/master?  YES -> NEW_COMMITS_ONLY only
All commits local?  YES -> aggressive rewrite OK
Pushed commits?  YES -> --force-with-lease required
Change fits existing commit?  YES -> fixup to that hash
History messy + all local?  YES -> consider reset --soft + rebuild
```

**Anti-patterns that break review:**
1. One commit for 3+ unrelated files
2. Test in separate commit from its implementation
3. Grouping by file type instead of feature/module
4. Rewriting pushed history without warning
5. `--force` instead of `--force-with-lease`
6. Leaving working directory dirty after committing
