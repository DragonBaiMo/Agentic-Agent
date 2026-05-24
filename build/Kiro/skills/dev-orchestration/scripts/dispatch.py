"""
dispatch.py — 模板渲染 + 上下文注入。
子命令: dispatch <phase>, dispatch --cross <template>
"""
import os
import re
import sys

from core import (
    PHASE_STEPS, PHASE_NAMES, PHASE_TEMPLATE, STEP_GROUPS,
    CROSS_CUTTING_TEMPLATES,
    find_state, load_state, get_project_root, get_template_path, map_sisyphus_path,
    run_context_pairs,
    find_next_pending_group,
    md_heading, md_kv,
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


def _print_preview_context(state_path, state, run_id=None):
    out = []
    out.append(md_heading("调度预览上下文"))
    out.append("")
    pairs = run_context_pairs(state_path, state)
    if run_id:
        pairs.append(("说明", "当前输出为指定 run 的只读预览；done/mark/redo/advance/gate 仍只作用于 ACTIVE_RUN"))
    out.append(md_kv(pairs))
    out.append("")
    out.append("---")
    out.append("")
    print("\n".join(out))


def _build_context(state, state_path):
    """从 state 构建模板变量字典。"""
    project_root = get_project_root(state_path)
    task = state["task_name"]

    log_dir = map_sisyphus_path(f".sisyphus/logs/{task}", state)
    plan_output = map_sisyphus_path(f".sisyphus/plans/{task}.md", state)
    intel_path = map_sisyphus_path(f".sisyphus/logs/{task}/intel-summary.md", state)
    decision_path = map_sisyphus_path(f".sisyphus/logs/{task}/decision.md", state)
    review_dir = map_sisyphus_path(".sisyphus/reviews", state)
    sync_dir = map_sisyphus_path(".sisyphus/sync", state)

    ctx = {
        "TASK_NAME": task,
        "PROJECT_ROOT": project_root,
        "MODE": state["mode"],
        "CURRENT_PHASE": state["current_phase"],
        "PIPELINE": " → ".join(state["pipeline"]),
        "LOG_DIR": log_dir,
        "PLAN_OUTPUT_PATH": plan_output,
        "INTEL_SUMMARY_PATH": intel_path,
        "DECISION_PATH": decision_path,
        "REVIEW_DIR": review_dir,
        "CONVENTIONS_PATH": "PROJECT_CONVENTIONS.md",
        "DOCTRINE_PATH": "IMPLEMENTATION_DOCTRINE.md",
        "CONTRACTS_PATH": "CONTRACTS.md",
        "INSTRUCTION_PACK_PATH": "dev-orchestration/references/subagent-instruction-pack.md",
        "GATE_REVIEW_SPEC_PATH": "dev-orchestration/references/gate-review-evidence.md",
        "SYNC_DIR": sync_dir,
    }

    # 已完成阶段列表
    completed = []
    for p in state["pipeline"]:
        if state["phases"][p]["status"] == "completed":
            completed.append(p)
    ctx["COMPLETED_PHASES"] = ", ".join(completed) if completed else "无"

    # 探索深度（按模式自动分级）
    depth_map = {
        "simple": "quick", "review": "quick",
        "fullstack": "thorough", "fullstack+design": "thorough",
    }
    ctx["EXPLORE_DEPTH"] = depth_map.get(state["mode"], "medium")

    # 无契约阶段时降级引用
    if "P5" not in state["pipeline"]:
        ctx["CONTRACTS_PATH"] = "N/A（本模式无契约阶段）"

    return ctx


def _render_template(template_path, ctx):
    """读取模板并替换占位符。"""
    if not os.path.isfile(template_path):
        print(f"## ❌ 模板不存在: `{template_path}`")
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 替换 {{VAR}}
    def replacer(match):
        key = match.group(1)
        return ctx.get(key, match.group(0))

    rendered = re.sub(r"\{\{(\w+)\}\}", replacer, content)

    # 检查是否有未替换的占位符
    remaining = re.findall(r"\{\{(\w+)\}\}", rendered)
    if remaining:
        unique = sorted(set(remaining))
        print(f"## ⚠️ 模板中有未替换的占位符: {', '.join(unique)}\n")
        print("这些变量未在上下文中定义。dispatch 指令可能不完整。\n")

    return rendered


def _validate_dispatch_phase(phase, state):
    """校验 dispatch 阶段有效性：管线归属、进度超前、已完成警告。"""
    pipeline = state["pipeline"]

    if phase not in pipeline:
        print(f"## ❌ 阶段 `{phase}` 不在当前管线中\n")
        print(f"当前管线: {' → '.join(pipeline)}")
        sys.exit(1)

    phase_idx = pipeline.index(phase)
    current_idx = state["current_phase_index"]

    if phase_idx > current_idx:
        cur = state["current_phase"]
        print(f"## ❌ 阶段 `{phase}` 尚未到达\n")
        print(f"当前阶段: {cur}（索引 {current_idx}）")
        print(f"目标阶段: {phase}（索引 {phase_idx}）")
        sys.exit(1)

    phase_data = state["phases"].get(phase, {})
    if phase_data.get("status") == "completed":
        print(f"⚠️ 此阶段已完成，以下为只读回看\n")


def _extract_cross_section(content, section_key):
    """从 X.md 渲染结果中提取指定 Cross section。"""
    marker = f"## Cross: {section_key}"
    start = content.find(marker)
    if start == -1:
        return None

    # 找下一个 "## Cross:" 或文件结尾
    next_marker = content.find("\n## Cross:", start + len(marker))
    if next_marker == -1:
        section = content[start:]
    else:
        # 回退到 --- 分隔符（如果存在）
        sep_pos = content.rfind("\n---\n", start + len(marker), next_marker)
        if sep_pos != -1:
            section = content[start:sep_pos]
        else:
            section = content[start:next_marker]

    return section.strip()


def cmd_dispatch_phase(phase, run_id=None):
    """渲染整个 Phase 模板。"""
    state_path, state = _require_state(run_id=run_id)
    _validate_dispatch_phase(phase, state)

    template_name = PHASE_TEMPLATE.get(phase)
    if not template_name:
        valid = ", ".join(sorted(PHASE_TEMPLATE.keys()))
        print(f"## ❌ 无效阶段: `{phase}`\n\n可用阶段: {valid}")
        sys.exit(1)

    template_path = get_template_path(template_name)
    ctx = _build_context(state, state_path)
    ctx["DISPATCH_PHASE"] = phase
    ctx["PHASE_NAME"] = PHASE_NAMES.get(phase, phase)

    # 注入已完成步骤
    phase_data = state.get("phases", {}).get(phase, {})
    completed_steps = phase_data.get("completed_steps", [])
    ctx["COMPLETED_STEPS"] = ", ".join(completed_steps) if completed_steps else "无"

    rendered = _render_template(template_path, ctx)
    _print_preview_context(state_path, state, run_id=run_id)
    print(rendered)

    # 进度摘要
    steps = PHASE_STEPS.get(phase, [])
    all_step_names = [s for s, _ in steps]
    remaining = [s for s in all_step_names if s not in completed_steps]
    print("")
    print("---")
    print("")
    if remaining:
        print(f"待完成步骤: {', '.join(remaining)}")
        print(f"完成后: `dev-orch done {phase} <step>`")
    else:
        print(f"所有步骤已完成。运行 `dev-orch gate {phase} --auto-advance`")


def cmd_dispatch(phase, step, run_id=None):
    """兼容旧调用：单步骤 dispatch 降级为 Phase 级加载。"""
    print(f"⚠️ 单步骤 dispatch 已停用。加载整个 Phase {phase} 模板。\n")
    cmd_dispatch_phase(phase, run_id=run_id)


def cmd_cross_cutting(template_name, run_id=None):
    """渲染横切 dispatch 模板（从 X.md 提取段落）。"""
    state_path, state = _require_state(run_id=run_id)

    if template_name not in CROSS_CUTTING_TEMPLATES:
        valid = ", ".join(sorted(CROSS_CUTTING_TEMPLATES.keys()))
        print(f"## ❌ 无效横切模板: `{template_name}`\n\n可用: {valid}")
        sys.exit(1)

    tfile, section_key = CROSS_CUTTING_TEMPLATES[template_name]
    template_path = get_template_path(tfile)
    ctx = _build_context(state, state_path)
    rendered = _render_template(template_path, ctx)
    _print_preview_context(state_path, state, run_id=run_id)

    # 提取 "## Cross: <section_key>" 到下一个 "## Cross:" 或文件结尾的内容
    section = _extract_cross_section(rendered, section_key)
    if section:
        print(section)
    else:
        print(f"## ⚠️ 未找到段落 `{section_key}`，输出完整横切模板\n")
        print(rendered)


def cmd_dispatch_group(phase):
    """渲染阶段内下一个待完成步骤组的所有模板。（保留兼容，内部已由 cmd_dispatch_phase 取代）"""
    cmd_dispatch_phase(phase)