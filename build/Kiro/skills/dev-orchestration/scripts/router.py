"""
router.py — 阶段路由 + 上下文恢复。
子命令: route [--verbose]
"""
import sys

from core import (
    PHASE_GATES, PHASE_NAMES, PHASE_STEPS, STEP_GROUPS,
    find_state, load_state, get_project_root, map_sisyphus_path,
    run_context_pairs,
    md_heading, md_table, md_kv, gate_status_icon, pipeline_str,
    find_next_pending_group,
)


def _require_state(run_id=None):
    path = find_state(run_id=run_id)
    if not path:
        if run_id:
            print(f"## ❌ 未找到 run-id: `{run_id}`\n")
            print("`--run-id` 仅支持只读查看已存在的 run。")
            sys.exit(1)
        print("## ❌ 未找到活跃项目\n")
        print("运行 `dev-orch init <mode> <task-name>` 初始化项目。")
        sys.exit(1)
    return path, load_state(path)


def cmd_route(verbose=False, run_id=None):
    """输出当前路由信息。"""
    state_path, state = _require_state(run_id=run_id)

    cur = state["current_phase"]
    pipeline = state["pipeline"]
    phases = state["phases"]
    gates = phases[cur]["gates"]

    total = len(gates)
    done = sum(1 for g in gates.values() if g.get("status") in ("passed", "skipped"))

    if verbose:
        _verbose_report(state_path, state, cur, pipeline, phases, gates, total, done)
    else:
        _standard_report(state_path, state, cur, gates, total, done)


def _standard_report(state_path, state, cur, gates, total, done):
    out = []
    out.append(md_heading("当前路由"))
    out.append("")
    out.append(md_kv([
        *run_context_pairs(state_path, state),
        ("阶段", f"{cur}（{PHASE_NAMES.get(cur, '')}）"),
        ("进度", f"{done}/{total} 门控通过"),
    ]))

    pending, is_parallel = find_next_pending_group(cur, state)
    if pending:
        step_names = [s for s, _ in pending]
        out.append("")
        out.append(md_heading("当前行动", 3))
        if is_parallel:
            out.append(f"运行 `dev-orch dispatch {cur}` 获取下一组指令（并行：{' + '.join(step_names)}）。")
        else:
            out.append(f"运行 `dev-orch dispatch {cur}` 获取下一步指令（{step_names[0]}）。")

    out.append("")
    out.append(md_heading("门控进度", 3))
    rows = []
    first_pending = True
    for gdef in PHASE_GATES.get(cur, []):
        gid = gdef["id"]
        gdata = gates.get(gid, {})
        status = gdata.get("status", "pending")
        marker = ""
        if status == "pending" and first_pending:
            marker = " ← 当前"
            first_pending = False
        rows.append([gid, f"{gate_status_icon(status)}{marker}"])
    out.append(md_table(["门控", "状态"], rows))
    print("\n".join(out))


def _verbose_report(state_path, state, cur, pipeline, phases, gates, total, done):
    out = []
    out.append(md_heading("上下文恢复报告"))

    # 项目概况
    out.append("")
    out.append(md_heading("项目概况", 3))
    completed_count = sum(1 for p in pipeline if phases[p]["status"] == "completed")
    out.append(md_kv([
        *run_context_pairs(state_path, state),
        ("项目", state["task_name"]),
        ("模式", state["mode"]),
        ("管线", pipeline_str(pipeline)),
        ("进度", f"{completed_count}/{len(pipeline)} 阶段完成"),
    ]))

    # 已完成阶段
    completed = [(p, PHASE_NAMES.get(p, ""), phases[p].get("completed_at", ""))
                 for p in pipeline if phases[p]["status"] == "completed"]
    if completed:
        out.append("")
        out.append(md_heading("已完成阶段及关键产出", 3))
        rows = []
        for pid, pname, ptime in completed:
            # 列出可能的产出文件
            outputs = _infer_outputs(pid, state["task_name"], state)
            rows.append([pid, pname, outputs])
        out.append(md_table(["阶段", "名称", "关键产出"], rows))

    # 当前阶段
    out.append("")
    out.append(md_heading(f"当前阶段：{cur}（{PHASE_NAMES.get(cur, '')}）", 3))
    out.append("")
    out.append("#### 门控进度")
    rows = []
    for gdef in PHASE_GATES.get(cur, []):
        gid = gdef["id"]
        gdata = gates.get(gid, {})
        status = gdata.get("status", "pending")
        rows.append([gid, f"{gate_status_icon(status)} {status}", gdef["desc"]])
    out.append(md_table(["门控", "状态", "说明"], rows))

    # 可用步骤组
    groups = STEP_GROUPS.get(cur, [])
    completed_steps = phases[cur].get("completed_steps", [])

    available_groups = []
    for group in groups:
        pending_in_group = [s for s in group if s not in completed_steps]
        if pending_in_group:
            available_groups.append((pending_in_group, len(group) > 1))

    if available_groups:
        out.append("")
        out.append("#### 待完成步骤组")
        rows = []
        for i, (steps, parallel) in enumerate(available_groups):
            label = " + ".join(steps)
            if parallel:
                label += "（并行）"
            marker = " ← 当前" if i == 0 else ""
            rows.append([f"组 {i+1}", label, marker])
        out.append(md_table(["组", "步骤", ""], rows))

    # 下一步
    pending, is_parallel = find_next_pending_group(cur, state)
    out.append("")
    out.append(md_heading("下一步行动", 3))
    if pending:
        step_names = [s for s, _ in pending]
        if is_parallel:
            out.append(f"1. 运行 `dev-orch dispatch {cur}` 获取指令（并行：{' + '.join(step_names)}）")
        else:
            out.append(f"1. 运行 `dev-orch dispatch {cur}` 获取指令（{step_names[0]}）")
        out.append("2. 执行指令 → 完成后 `mark` 标记门控")
        out.append("3. 重复直到所有门控通过")
    else:
        if done >= total:
            out.append("所有门控已通过。运行 `dev-orch advance` 推进到下一阶段。")
        else:
            out.append("部分门控未通过但无可用步骤。检查门控状态并手动标记。")

    print("\n".join(out))


def _infer_outputs(phase, task_name, state):
    """根据阶段推断可能的产出路径。"""
    decision_path = map_sisyphus_path(f".sisyphus/logs/{task_name}/decision.md", state)
    intel_path = map_sisyphus_path(f".sisyphus/logs/{task_name}/intel-summary.md", state)
    plan_path = map_sisyphus_path(f".sisyphus/plans/{task_name}.md", state)

    outputs_map = {
        "P0": f"`{decision_path}`",
        "P1": f"`{intel_path}`",
        "P2": f"`{plan_path}`",
        "P3": "方案文档",
        "P4": "`PROJECT_CONVENTIONS.md`, `IMPLEMENTATION_DOCTRINE.md`",
        "P5": "`CONTRACTS.md`, 共享类型",
        "P6A": "后端代码 + 测试",
        "P6B": "前端代码 + 测试",
        "P7": "集成测试通过",
        "P8": "交付摘要",
    }
    return outputs_map.get(phase, "—")
