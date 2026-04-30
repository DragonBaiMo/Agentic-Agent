---
description: "生成当前会话的交接摘要，用于在新会话中无缝继续工作。"
---

# Handoff — Session Context Summary

Generate a structured handoff document capturing the current session state so work can resume seamlessly in a new session.

## Step 1: Gather Context

Run these commands in parallel to collect concrete data:

```
git diff --stat HEAD~10..HEAD
git status --porcelain
```

Also read any active todo state if available.

## Step 2: Synthesize

Analyze gathered data to identify:
- What the user originally asked for (verbatim)
- What was completed this session
- What tasks remain or are in-progress
- Which files were modified or are relevant
- Any decisions, constraints, or patterns established

## Step 3: Write Handoff File

Save the summary to `.sisyphus/handoff-<YYYYMMDD-HHMMSS>.md` using this exact structure:

```
HANDOFF CONTEXT
===============

USER REQUESTS (AS-IS)
---------------------
- [Verbatim — do not paraphrase]

GOAL
----
[Single sentence: what should happen next]

WORK COMPLETED
--------------
- [First-person bullets: what was done, with file paths where relevant]

CURRENT STATE
-------------
- [Build/test status, environment state, any partial work]

PENDING TASKS
-------------
- [Unfinished planned work, blockers, next logical steps]

KEY FILES
---------
- path/to/file - role (max 10, prioritized by importance)

IMPORTANT DECISIONS
-------------------
- [Technical decisions made and why; trade-offs; conventions established]

EXPLICIT CONSTRAINTS
--------------------
- [Verbatim constraints from user or AGENTS.md — or "None"]
```

## Rules

- USER REQUESTS and EXPLICIT CONSTRAINTS must be verbatim — never paraphrase
- Use workspace-relative paths throughout
- No sensitive data (API keys, credentials)
- KEY FILES: max 10 entries, derived from git diff/status
- Keep GOAL to one sentence

## Step 4: Instruct User

After saving the file, tell the user:

```
Handoff saved to .sisyphus/handoff-<timestamp>.md

To continue in a new session:
1. Open a new OpenCode session (press 'n' in TUI, or run `opencode`)
2. Paste the HANDOFF CONTEXT as your first message
3. Append your next request: "Continue from the handoff above. [task]"
```
