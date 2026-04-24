"""
state.py — 状态管理模块。
子命令: init, mark, current, advance
"""
import os
import sys
from pathlib import Path

from core import (
    MODE_PIPELINES, PHASE_GATES, PHASE_NAMES, PHASE_STEPS, STEP_GROUPS,
    ACTIVE_RUN_FILE,
    find_state, load_state, save_state, now_iso, get_project_root,
    read_active_run_id, run_context_pairs,
    validate_gate_review_evidence,
    find_next_pending_group,
    md_heading, md_table, md_kv, gate_status_icon, pipeline_str,
)

# redo 迭代上限
MAX_REDO_WARN = 3
MAX_REDO_HALT = 5


def _find_sisyphus_root(start_dir=None):
    """从当前目录向上查找 .sisyphus 根目录。"""
    d = Path(start_dir or os.getcwd()).resolve()
    while True:
        sisy_dir = d / ".sisyphus"
        if sisy_dir.is_dir():
            return str(sisy_dir)
        parent = d.parent
        if parent == d:
            return None
        d = parent


def _new_run_id(runs_dir):
    """生成唯一 run-id（Windows 友好，无冒号）。"""
    base = now_iso().replace(":", "").replace("T", "-")
    run_id = base
    suffix = 1
    while os.path.exists(os.path.join(runs_dir, run_id)):
        run_id = f"{base}-{suffix}"
        suffix += 1
    return run_id


def _require_state(run_id=None):
    """查找并加载 state.json，找不到则报错退出。"""
    path = find_state(run_id=run_id)
    if not path:
        if run_id:
            print(f"## ❌ 未找到 run-id: `{run_id}`\n")
            print("在当前目录或上级目录中未发现该 run-id 对应的 `.sisyphus/runs/<run-id>/state.json`。\n")
            print("`--run-id` 仅支持只读查看已存在的 run。")
            sys.exit(1)
        print("## ❌ 未找到活跃项目\n")
        print("在当前目录或上级目录中未发现 ACTIVE_RUN 对应状态或 `.sisyphus/state.json`。\n")
        print("运行 `dev-orch init <mode> <task-name>` 初始化项目。")
        sys.exit(1)
    return path, load_state(path)


# ─── init ───

def cmd_init(mode, task_name):
    """初始化项目状态。"""
    if mode not in MODE_PIPELINES:
        modes = ", ".join(sorted(MODE_PIPELINES.keys()))
        print(f"## ❌ 无效模式: `{mode}`\n")
        print(f"可选模式: {modes}")
        sys.exit(1)

    pipeline = MODE_PIPELINES[mode]
    state_dir = os.path.join(os.getcwd(), ".sisyphus")
    runs_dir = os.path.join(state_dir, "runs")
    os.makedirs(runs_dir, exist_ok=True)

    run_id = _new_run_id(runs_dir)
    run_dir = os.path.join(runs_dir, run_id)
    state_path = os.path.join(run_dir, "state.json")
    run_root_rel = f".sisyphus/runs/{run_id}"

    # 构建初始阶段数据
    phases = {}
    for phase_id in pipeline:
        gates = {}
        for gate_def in PHASE_GATES.get(phase_id, []):
            gates[gate_def["id"]] = {"status": "pending"}
        phases[phase_id] = {
            "status": "pending",
            "gates": gates,
            "completed_steps": [],
        }
    phases[pipeline[0]]["status"] = "in_progress"

    state = {
        "run_id": run_id,
        "run_root": run_root_rel,
        "task_name": task_name,
        "mode": mode,
        "pipeline": pipeline,
        "current_phase": pipeline[0],
        "current_phase_index": 0,
        "created_at": now_iso(),
        "phases": phases,
    }

    # 创建 run 目录结构
    log_dir = os.path.join(run_dir, "logs", task_name)
    plans_dir = os.path.join(run_dir, "plans")
    sync_dir = os.path.join(run_dir, "sync")
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(plans_dir, exist_ok=True)
    os.makedirs(sync_dir, exist_ok=True)

    save_state(state_path, state)

    active_run_path = os.path.join(state_dir, ACTIVE_RUN_FILE)
    with open(active_run_path, "w", encoding="utf-8") as f:
        f.write(run_id)

    # 输出 Markdown
    out = []
    out.append(md_heading("项目初始化完成"))
    out.append("")
    out.append(md_kv([
        ("运行 ID", run_id),
        ("项目名称", task_name),
        ("模式", f"{mode}"),
        ("阶段管线", pipeline_str(pipeline)),
        ("当前阶段", f"{pipeline[0]}（{PHASE_NAMES.get(pipeline[0], '')}）"),
    ]))
    out.append("")
    out.append(md_heading("下一步", 3))
    out.append("运行 `dev-orch route` 获取当前阶段指引。")
    print("\n".join(out))


# ─── mark ───

def cmd_mark(phase, gate_id, status, reason=None):
    """标记门控状态。"""
    state_path, state = _require_state()

    if status not in ("passed", "skipped"):
        print("## ❌ 状态必须为 `passed` 或 `skipped`")
        sys.exit(1)

    if status == "passed" and not reason:
        print("## ❌ 标记 passed 必须提供 review 证据文件路径\n")
        print("`dev-orch mark <phase> <gate> passed \"<review-path>\"`")
        sys.exit(1)

    if status == "skipped" and not reason:
        print("## ❌ 跳过门控必须提供原因\n")
        print("`dev-orch mark <phase> <gate> skipped \"原因\"`")
        sys.exit(1)

    phase_data = state.get("phases", {}).get(phase)
    if not phase_data:
        print(f"## ❌ 阶段 `{phase}` 不在当前管线中")
        sys.exit(1)

    gates = phase_data.get("gates", {})
    if gate_id not in gates:
        valid = ", ".join(gates.keys())
        print(f"## ❌ 门控 `{gate_id}` 不存在于阶段 `{phase}`\n")
        print(f"可用门控: {valid}")
        sys.exit(1)

    if status == "passed":
        project_root = get_project_root(state_path)
        ok, detail = validate_gate_review_evidence(project_root, reason, phase, gate_id)
        if not ok:
            print("## ❌ review 证据校验失败\n")
            print(f"门控: {phase}/{gate_id}")
            print(f"路径: {reason}")
            print(f"原因: {detail}")
            sys.exit(1)

    gates[gate_id] = {
        "status": status,
        "updated_at": now_iso(),
    }
    if reason:
        gates[gate_id]["reason"] = reason

    save_state(state_path, state)

    # 统计
    total = len(gates)
    done = sum(1 for g in gates.values() if g.get("status") in ("passed", "skipped"))

    out = []
    out.append(md_heading("门控已更新"))
    out.append("")
    out.append(md_kv([
        ("阶段", f"{phase}（{PHASE_NAMES.get(phase, '')}）"),
        ("门控", f"{gate_id} → **{status}**"),
        ("阶段进度", f"{done}/{total} 门控通过"),
    ]))
    out.append("")
    out.append(md_heading("剩余门控", 3))

    rows = []
    for gid, gdata in gates.items():
        icon = gate_status_icon(gdata.get("status", "pending"))
        gdesc = ""
        for gdef in PHASE_GATES.get(phase, []):
            if gdef["id"] == gid:
                gdesc = gdef["desc"]
                break
        rows.append([gid, f"{icon} {gdata.get('status', 'pending')}", gdesc])

    out.append(md_table(["门控", "状态", "说明"], rows))
    print("\n".join(out))


# ─── done ───

def cmd_done(phase, step_names):
    """标记步骤为已完成。"""
    state_path, state = _require_state()

    phase_data = state.get("phases", {}).get(phase)
    if not phase_data:
        print(f"## ❌ 阶段 `{phase}` 不在当前管线中")
        sys.exit(1)

    valid_steps = [s for s, _ in PHASE_STEPS.get(phase, [])]
    completed = phase_data.setdefault("completed_steps", [])

    marked = []
    already = []
    invalid = []

    for step in step_names:
        if step not in valid_steps:
            invalid.append(step)
        elif step in completed:
            already.append(step)
        else:
            completed.append(step)
            marked.append(step)

    if invalid:
        valid = ", ".join(valid_steps)
        print(f"## ❌ 无效步骤: {', '.join(invalid)}\n\n阶段 `{phase}` 可用步骤: {valid}")
        sys.exit(1)

    save_state(state_path, state)

    out = []
    out.append(md_heading("步骤已标记完成"))
    out.append("")
    out.append(md_kv([
        ("阶段", f"{phase}（{PHASE_NAMES.get(phase, '')}）"),
        ("已标记", ", ".join(marked) if marked else "无（均已完成）"),
    ]))

    if already:
        out.append(f"- **已跳过**（重复）: {', '.join(already)}")

    # 显示下一组
    pending, is_parallel = find_next_pending_group(phase, state)
    out.append("")
    if pending:
        step_names_next = [s for s, _ in pending]
        if is_parallel:
            out.append(f"下一组（并行）：{' + '.join(step_names_next)} → `dev-orch dispatch {phase}`")
        else:
            out.append(f"下一步：{step_names_next[0]} → `dev-orch dispatch {phase}`")
    else:
        out.append(f"所有步骤已完成 → `dev-orch gate {phase}` 验证门控")

    print("\n".join(out))


# ─── redo ───

def cmd_redo(phase, step_names, force=False):
    """将步骤重置为未完成（支持迭代循环）。"""
    state_path, state = _require_state()

    phase_data = state.get("phases", {}).get(phase)
    if not phase_data:
        print(f"## ❌ 阶段 `{phase}` 不在当前管线中")
        sys.exit(1)

    if phase_data["status"] == "completed":
        print("## ❌ 无法重置已完成阶段\n")
        print(f"阶段 `{phase}` 已完成，只能重置当前活跃阶段。")
        print("如需回退，请手动修改状态。")
        sys.exit(1)

    valid_steps = [s for s, _ in PHASE_STEPS.get(phase, [])]
    completed = phase_data.setdefault("completed_steps", [])

    reset = []
    not_done = []
    invalid = []

    for step in step_names:
        if step not in valid_steps:
            invalid.append(step)
        elif step not in completed:
            not_done.append(step)
        else:
            completed.remove(step)
            reset.append(step)

    if invalid:
        valid = ", ".join(valid_steps)
        print(f"## ❌ 无效步骤: {', '.join(invalid)}\n\n阶段 `{phase}` 可用步骤: {valid}")
        sys.exit(1)

    # 重置所有门控（步骤变更后所有验证点需重新确认）
    gates_reset = 0
    if reset:
        for gate_info in phase_data.get("gates", {}).values():
            if gate_info["status"] != "pending":
                gate_info["status"] = "pending"
                gates_reset += 1

    # 递增迭代计数器
    iterations = phase_data.setdefault("iterations", {})
    for step in reset:
        iterations[step] = iterations.get(step, 0) + 1

    # 检查迭代上限
    halted = []
    warned = []
    for step in reset:
        count = iterations.get(step, 0)
        if count >= MAX_REDO_HALT:
            halted.append((step, count))
        elif count >= MAX_REDO_WARN:
            warned.append((step, count))

    if halted and not force:
        for step, count in halted:
            print(f"## 🛑 已达迭代上限\n")
            print(f"步骤 `{step}` 已迭代 {count} 轮，超出上限 {MAX_REDO_HALT}。\n")
        print("建议：")
        print("- 运行 `dev-orch dispatch --cross blocking-resolution` 寻求解决方案")
        print("- 或使用 `dev-orch redo --force` 强制继续")
        sys.exit(1)

    save_state(state_path, state)

    out = []
    out.append(md_heading("步骤已重置"))
    out.append("")
    out.append(md_kv([
        ("阶段", f"{phase}（{PHASE_NAMES.get(phase, '')}）"),
        ("已重置", ", ".join(reset) if reset else "无"),
    ]))
    if gates_reset > 0:
        out.append(f"- **门控已重置**: {gates_reset} 个门控恢复为 pending")

    if not_done:
        out.append(f"- **已跳过**（本就未完成）: {', '.join(not_done)}")

    # 显示迭代次数
    iter_info = [(s, iterations.get(s, 0)) for s in reset if iterations.get(s, 0) > 0]
    if iter_info:
        out.append("")
        out.append("迭代轮次：" + ", ".join(f"{s} → Round {n+1}" for s, n in iter_info))

    if warned:
        out.append("")
        for step, count in warned:
            out.append(f"⚠️ 步骤 `{step}` 第 {count} 轮迭代，考虑是否需要改变方向")

    # 显示下一组
    pending, is_parallel = find_next_pending_group(phase, state)
    out.append("")
    if pending:
        step_names_next = [s for s, _ in pending]
        if is_parallel:
            out.append(f"下一组（并行）：{' + '.join(step_names_next)} → `dev-orch dispatch {phase}`")
        else:
            out.append(f"下一步：{step_names_next[0]} → `dev-orch dispatch {phase}`")

    print("\n".join(out))


def cmd_current(run_id=None):
    """显示当前状态。"""
    state_path, state = _require_state(run_id=run_id)

    cur = state["current_phase"]
    pipeline = state["pipeline"]
    phases = state["phases"]

    out = []
    out.append(md_heading("当前状态"))
    out.append("")
    out.append(md_kv([
        *run_context_pairs(state_path, state),
        ("项目", state["task_name"]),
        ("模式", state["mode"]),
        ("当前阶段", f"{cur}（{PHASE_NAMES.get(cur, '')}）"),
        ("阶段状态", phases[cur]["status"]),
    ]))

    # 已完成阶段
    completed = [(p, PHASE_NAMES.get(p, ""), phases[p].get("completed_at", ""))
                 for p in pipeline if phases[p]["status"] == "completed"]
    if completed:
        out.append("")
        out.append(md_heading("已完成阶段", 3))
        out.append(md_table(["阶段", "名称", "完成时间"],
                            [[c[0], c[1], c[2]] for c in completed]))

    # 当前阶段门控
    out.append("")
    out.append(md_heading("当前阶段门控", 3))
    gates = phases[cur]["gates"]
    rows = []
    for gdef in PHASE_GATES.get(cur, []):
        gid = gdef["id"]
        gdata = gates.get(gid, {})
        status = gdata.get("status", "pending")
        rows.append([gid, f"{gate_status_icon(status)} {status}", gdef["desc"]])
    out.append(md_table(["门控", "状态", "说明"], rows))

    # 下一步
    pending, is_parallel = find_next_pending_group(cur, state)
    if pending:
        step_names_next = [s for s, _ in pending]
        out.append("")
        out.append(md_heading("下一步", 3))
        if is_parallel:
            out.append(f"运行 `dev-orch dispatch {cur}` 获取指令（并行：{' + '.join(step_names_next)}）。")
        else:
            out.append(f"运行 `dev-orch dispatch {cur}` 获取指令（{step_names_next[0]}）。")

    print("\n".join(out))


def cmd_history(task_filter=None):
    """列出 runs 历史并标记 ACTIVE_RUN。"""
    sisy_root = _find_sisyphus_root()
    if not sisy_root:
        print("## ❌ 未找到 .sisyphus 目录\n")
        print("运行 `dev-orch init <mode> <task-name>` 初始化项目。")
        sys.exit(1)

    runs_dir = os.path.join(sisy_root, "runs")
    active_run_path = os.path.join(sisy_root, ACTIVE_RUN_FILE)
    active_run_id = read_active_run_id(sisy_root)

    normalized_filter = (task_filter or "").strip().lower()

    rows = []
    if os.path.isdir(runs_dir):
        run_ids = [d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
        run_ids.sort(reverse=True)

        for run_id in run_ids:
            run_state_path = os.path.join(runs_dir, run_id, "state.json")
            if not os.path.isfile(run_state_path):
                continue
            try:
                run_state = load_state(run_state_path)
            except Exception:
                continue

            task_name = run_state.get("task_name", "—")
            if normalized_filter and normalized_filter not in task_name.lower():
                continue

            marker = "*" if run_id == active_run_id else ""
            rows.append([
                marker,
                run_id,
                task_name,
                run_state.get("mode", "—"),
                run_state.get("created_at", "—"),
                run_state.get("current_phase", "—"),
            ])

    out = []
    out.append(md_heading("运行历史"))
    out.append("")
    out.append(md_kv([
        ("当前 ACTIVE_RUN", active_run_id or "未设置"),
        ("task 过滤", task_filter or "无"),
    ]))
    out.append("")

    if rows:
        out.append(md_table(["当前", "run-id", "task_name", "mode", "created_at", "current_phase"], rows))
    else:
        if task_filter:
            out.append("未找到匹配该 task 关键字的 run。")
        else:
            out.append("未发现 `.sisyphus/runs/*/state.json` 历史记录。")

    print("\n".join(out))


# ─── advance ───

def cmd_advance():
    """推进到下一阶段。"""
    state_path, state = _require_state()

    cur = state["current_phase"]
    pipeline = state["pipeline"]
    phases = state["phases"]
    idx = state["current_phase_index"]

    # 检查当前阶段门控
    gates = phases[cur]["gates"]
    pending = [gid for gid, g in gates.items() if g.get("status") not in ("passed", "skipped")]

    if pending:
        out = []
        out.append(md_heading("无法推进 — 门控未通过"))
        out.append("")
        out.append(md_kv([("当前阶段", f"{cur}（{PHASE_NAMES.get(cur, '')}）")]))
        out.append("")
        out.append(md_heading("阻塞门控", 3))
        rows = []
        for gid in pending:
            gdesc = ""
            for gdef in PHASE_GATES.get(cur, []):
                if gdef["id"] == gid:
                    gdesc = gdef["desc"]
                    break
            rows.append([gid, "⏳ pending", gdesc])
        out.append(md_table(["门控", "状态", "说明"], rows))
        out.append("")
        out.append("必须解决以上阻塞门控后才能推进。")
        print("\n".join(out))
        sys.exit(1)

    # 标记当前阶段完成
    phases[cur]["status"] = "completed"
    phases[cur]["completed_at"] = now_iso()

    # 检查是否到最后
    if idx + 1 >= len(pipeline):
        state["current_phase"] = cur
        save_state(state_path, state)
        out = []
        out.append(md_heading("🎉 项目完成"))
        out.append("")
        out.append(f"所有 {len(pipeline)} 个阶段已完成。项目交付就绪。")
        print("\n".join(out))
        return

    # 推进
    next_phase = pipeline[idx + 1]
    state["current_phase"] = next_phase
    state["current_phase_index"] = idx + 1
    phases[next_phase]["status"] = "in_progress"
    save_state(state_path, state)

    out = []
    out.append(md_heading("阶段推进成功"))
    out.append("")
    out.append(md_kv([
        ("完成", f"{cur}（{PHASE_NAMES.get(cur, '')}）"),
        ("进入", f"{next_phase}（{PHASE_NAMES.get(next_phase, '')}）"),
        ("下一步", f"运行 `dev-orch route` 获取 {next_phase} 指引"),
    ]))
    print("\n".join(out))
