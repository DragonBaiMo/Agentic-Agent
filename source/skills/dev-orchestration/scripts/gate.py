"""
gate.py — 门控验证模块。
子命令: gate <phase> [--auto-advance]
"""
import sys

from core import (
    PHASE_GATES, PHASE_NAMES,
    find_state, load_state, save_state, get_project_root, verify_gate, now_iso,
    md_heading, md_table, md_kv, gate_status_icon,
)


def _require_state():
    path = find_state()
    if not path:
        print("## ❌ 未找到活跃项目\n")
        print("运行 `dev-orch init <mode> <task-name>` 初始化项目。")
        sys.exit(1)
    return path, load_state(path)


def cmd_gate(phase, auto_advance=False):
    """验证指定阶段的所有门控。auto_advance=True 时全通过自动推进。"""
    state_path, state = _require_state()

    if phase not in PHASE_GATES:
        valid = ", ".join(sorted(PHASE_GATES.keys()))
        print(f"## ❌ 无效阶段: `{phase}`\n\n可用阶段: {valid}")
        sys.exit(1)

    project_root = get_project_root(state_path)
    gate_defs = PHASE_GATES[phase]

    out = []
    out.append(md_heading(f"门控验证: {phase}（{PHASE_NAMES.get(phase, '')}）"))
    out.append("")
    out.append(md_heading("验证结果", 3))

    rows = []
    all_pass = True
    suggestions = []

    for gdef in gate_defs:
        status, detail = verify_gate(gdef, state, project_root)
        icon = gate_status_icon(status)
        method_label = gdef["method"]
        rows.append([gdef["id"], f"{icon} {status}", method_label, detail or "—"])

        if status not in ("passed", "skipped"):
            all_pass = False
            suggestions.append((gdef["id"], gdef["desc"], _suggest_fix(gdef, phase)))

    out.append(md_table(["门控", "状态", "验证方式", "详情"], rows))

    # 结论
    total = len(gate_defs)
    passed = total - len(suggestions)
    out.append("")
    out.append(md_heading("结论", 3))
    if all_pass:
        if auto_advance:
            # 自动推进
            pipeline = state["pipeline"]
            phases = state["phases"]
            idx = state["current_phase_index"]

            phases[phase]["status"] = "completed"
            phases[phase]["completed_at"] = now_iso()

            if idx + 1 >= len(pipeline):
                state["current_phase"] = phase
                save_state(state_path, state)
                out.append(f"**全部通过** — {total}/{total} 门控通过\n")
                out.append("🎉 所有阶段已完成。项目交付就绪。")
            else:
                next_phase = pipeline[idx + 1]
                state["current_phase"] = next_phase
                state["current_phase_index"] = idx + 1
                phases[next_phase]["status"] = "in_progress"
                save_state(state_path, state)
                out.append(f"**全部通过且已推进** — {total}/{total} 门控通过\n")
                out.append(md_kv([
                    ("完成", f"{phase}（{PHASE_NAMES.get(phase, '')}）"),
                    ("进入", f"{next_phase}（{PHASE_NAMES.get(next_phase, '')}）"),
                    ("下一步", f"运行 `dev-orch dispatch {next_phase}` 获取指令"),
                ]))
        else:
            out.append(f"**可以推进** — {total}/{total} 门控通过\n")
            out.append("运行 `dev-orch advance` 推进到下一阶段。")
    else:
        out.append(f"**不可推进** — {len(suggestions)}/{total} 门控未通过")

    # 解决建议
    if suggestions:
        out.append("")
        out.append(md_heading("解决建议", 3))
        for i, (gid, gdesc, fix) in enumerate(suggestions, 1):
            out.append(f"{i}. `{gid}`: {fix}")

    print("\n".join(out))


def _suggest_fix(gdef, phase):
    """生成门控修复建议。"""
    method = gdef["method"]
    gid = gdef["id"]

    if method == "state_marker":
        return (
            "先生成 review 文件，再运行 "
            f"`dev-orch mark {phase} {gid} passed \"<review-path>\"`"
        )
    elif method == "file_check":
        return f"创建 `{gdef['path']}`"
    elif method == "dir_check":
        return f"创建目录 `{gdef['path']}`"
    elif method == "content_check":
        return f"确保 `{gdef['path']}` 包含 '{gdef.get('contains', '')}'"
    return "手动检查"
