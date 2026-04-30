"""
dev-orchestration CLI 入口。
将子命令路由到对应模块。
"""
import sys
import os

# 确保 scripts/ 目录在 import 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

USAGE = """## dev-orch — 开发编排 CLI

### 命令列表

| 命令 | 用途 |
|------|------|
| `dev-orch init <mode> <task-name>` | 初始化项目 |
| `dev-orch route [--run-id <id>] [--verbose]` | 获取指定 run 的当前路由（只读） |
| `dev-orch dispatch <phase> [--run-id <id>]` | 获取指定 run 的 Phase 完整指令（只读） |
| `dev-orch dispatch --cross <template> [--run-id <id>]` | 获取指定 run 的横切 dispatch（只读） |
| `dev-orch gate <phase>` | 检查门控 |
| `dev-orch gate <phase> --auto-advance` | 检查门控，全通过自动推进 |
| `dev-orch mark <phase> <gate> passed "<review-path>"` | 标记门控通过（需 review 证据） |
| `dev-orch mark <phase> <gate> skipped "<reason>"` | 跳过门控 |
| `dev-orch done <phase> <step> [step2 ...]` | 标记步骤完成 |
| `dev-orch redo <phase> <step> [step2 ...] [--force]` | 重置步骤，启动新一轮迭代 |
| `dev-orch advance` | 推进阶段 |
| `dev-orch current [--run-id <id>]` | 查看指定 run 的当前状态（只读） |
| `dev-orch history [--task <keyword>]` | 查看 run 历史，可按 task_name 过滤 |
"""


def _extract_option(args, option, usage):
    remaining = list(args)
    value = None
    while option in remaining:
        idx = remaining.index(option)
        if idx + 1 >= len(remaining):
            print(f"## ❌ 用法错误\n\n`{usage}`")
            sys.exit(1)
        value = remaining[idx + 1]
        del remaining[idx:idx + 2]
    return value, remaining


def _extract_flag(args, flag):
    remaining = [arg for arg in args if arg != flag]
    return len(remaining) != len(args), remaining

def main():
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        sys.exit(0)

    cmd = args[0]

    if cmd == "init":
        from state import cmd_init
        if len(args) < 3:
            print("## ❌ 用法错误\n\n`dev-orch init <mode> <task-name>`")
            sys.exit(1)
        cmd_init(args[1], args[2])

    elif cmd == "route":
        from router import cmd_route
        run_id, route_args = _extract_option(args[1:], "--run-id", "dev-orch route [--run-id <id>] [--verbose]")
        verbose, route_args = _extract_flag(route_args, "--verbose")
        if route_args:
            print("## ❌ 用法错误\n\n`dev-orch route [--run-id <id>] [--verbose]`")
            sys.exit(1)
        cmd_route(verbose=verbose, run_id=run_id)

    elif cmd == "dispatch":
        from dispatch import cmd_dispatch, cmd_cross_cutting, cmd_dispatch_phase
        dispatch_args = args[1:]
        run_id, dispatch_args = _extract_option(
            dispatch_args,
            "--run-id",
            "dev-orch dispatch <phase> [--run-id <id>]\n`dev-orch dispatch --cross <template-name> [--run-id <id>]`",
        )
        if "--cross" in dispatch_args:
            idx = dispatch_args.index("--cross")
            if idx + 1 >= len(dispatch_args) or len(dispatch_args) != 2:
                print("## ❌ 用法错误\n\n`dev-orch dispatch --cross <template-name> [--run-id <id>]`")
                sys.exit(1)
            cmd_cross_cutting(dispatch_args[idx + 1], run_id=run_id)
        else:
            if not dispatch_args:
                print("## ❌ 用法错误\n\n`dev-orch dispatch <phase> [--run-id <id>]`")
                sys.exit(1)
            if len(dispatch_args) == 1:
                cmd_dispatch_phase(dispatch_args[0], run_id=run_id)
            else:
                cmd_dispatch(dispatch_args[0], dispatch_args[1], run_id=run_id)  # 兼容降级

    elif cmd == "gate":
        from gate import cmd_gate
        if len(args) < 2:
            print("## ❌ 用法错误\n\n`dev-orch gate <phase> [--auto-advance]`")
            sys.exit(1)
        auto_advance = "--auto-advance" in args
        phase = [a for a in args[1:] if not a.startswith("--")][0]
        cmd_gate(phase, auto_advance=auto_advance)

    elif cmd == "mark":
        from state import cmd_mark
        if len(args) < 4:
            print("## ❌ 用法错误\n\n`dev-orch mark <phase> <gate> passed \"<review-path>\"`\n`dev-orch mark <phase> <gate> skipped \"<reason>\"`")
            sys.exit(1)
        reason = args[4] if len(args) > 4 else None
        cmd_mark(args[1], args[2], args[3], reason)

    elif cmd == "advance":
        from state import cmd_advance
        cmd_advance()

    elif cmd == "done":
        from state import cmd_done
        if len(args) < 3:
            print("## ❌ 用法错误\n\n`dev-orch done <phase> <step> [step2 ...]`")
            sys.exit(1)
        cmd_done(args[1], args[2:])

    elif cmd == "redo":
        from state import cmd_redo
        force = "--force" in args
        redo_args = [a for a in args[1:] if a != "--force"]
        if len(redo_args) < 2:
            print("## ❌ 用法错误\n\n`dev-orch redo <phase> <step> [step2 ...] [--force]`")
            sys.exit(1)
        cmd_redo(redo_args[0], redo_args[1:], force=force)

    elif cmd == "current":
        from state import cmd_current
        run_id, current_args = _extract_option(args[1:], "--run-id", "dev-orch current [--run-id <id>]")
        if current_args:
            print("## ❌ 用法错误\n\n`dev-orch current [--run-id <id>]`")
            sys.exit(1)
        cmd_current(run_id=run_id)

    elif cmd == "history":
        from state import cmd_history
        task_filter, history_args = _extract_option(args[1:], "--task", "dev-orch history [--task <keyword>]")
        if history_args:
            print("## ❌ 用法错误\n\n`dev-orch history [--task <keyword>]`")
            sys.exit(1)
        cmd_history(task_filter=task_filter)

    else:
        print(f"## ❌ 未知命令: `{cmd}`\n")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()