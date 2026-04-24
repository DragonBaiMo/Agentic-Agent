---
name: todo-management
description: Copilot 使用 Todo 的最小规则。
applyTo: "**"
---

## Conditions for Creating a Todo

Create a Todo only in the following cases:

* The task contains 3 or more explicit steps
* The user asks for multiple independent tasks at once
* You begin working on a plan file under `.sisyphus/plans/`

Do not create a Todo for the following cases:

* A single simple one-step task
* Pure Q&A, clarification, or explanation
* Read-only file access, searching, or status checking

## Item Format

Each item must include:

* WHERE: the specific file path; if multiple files are involved, write “multiple files, see subtasks”
* WHY: why this work is needed
* HOW: the specific implementation approach
* EXPECTED_RESULT: the observable completion result

Vague wording is prohibited, such as “fix bug” or “update config.”

## Status Rules

The only allowed status transition is:

pending -> in_progress -> completed

The following must be observed:

* Before starting work, first mark the item as `in_progress`
* At any given time, only one item may be `in_progress`
* As soon as an item is fully completed, immediately mark it as `completed`
* If any known unresolved issue still exists, it must not be marked as `completed`
* Do not start the next item before the current `in_progress` item is completed

## Update Rules

Update the Todo only when there is observable progress, for example:

* A file has been modified
* Tests have been run
* An error has been resolved

Do not update the Todo merely because you read a file, searched content, or checked status.

## Prohibited Behaviors

* Marking multiple items as completed in a batch
* Marking an item as `completed` while known outstanding issues remain
* Starting the next item while the current item is still `in_progress`
* Having an item without `WHERE` or `HOW`
* Creating a Todo for a trivial one-step task

## Example

TODO LIST

[in_progress] Add response header parsing logic for rate limiting
WHERE: `src/shared/http/rate-limit-parser.ts` (new file)
WHY: The retry logic needs to obtain the wait time from `X-RateLimit-Reset`
HOW: Parse the response headers and return a structure like `{ reset, remaining }`
EXPECTED_RESULT: Unit tests pass, and no new type errors are introduced

[pending] Integrate the parsing logic into the retry Hook
WHERE: `src/hooks/retry/retry-hook.ts`, around line 45
WHY: The current retry logic ignores rate limit response headers, which may cause a 429 retry storm
HOW: Import the parser and prioritize the reset time before the default exponential backoff
EXPECTED_RESULT: Retry tests pass, and 429 retry loops no longer occur

The second item must remain `pending` until the first item is marked as `completed`.