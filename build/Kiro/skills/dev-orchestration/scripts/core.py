"""
dev-orchestration 核心库。
被其他脚本 import，不直接 CLI 调用。
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

# ─── Phase 名称映射 ───
PHASE_NAMES = {
    "P0": "分流决策",
    "P1": "意图澄清 + 情报",
    "P2": "规划 + 审查",
    "P3": "方案设计 + 审核循环",
    "P4": "编排落地",
    "P5": "契约基础",
    "P6A": "后端实现",
    "P6B": "前端实现",
    "P7": "集成联调",
    "P8": "交付验证",
}

# ─── 门控定义（硬编码，不可被模型篡改） ───
PHASE_GATES = {
    "P0": [
        {"id": "path_selected",    "desc": "模式和路径已确定",           "method": "state_marker"},
        {"id": "decision_logged",  "desc": "decision.md 已创建",        "method": "file_check", "path": ".sisyphus/logs/{task}/decision.md"},
    ],
    "P1": [
        {"id": "ambiguity_resolved",    "desc": "所有歧义已解决",         "method": "state_marker"},
        {"id": "knowledge_gaps_filled", "desc": "知识盲区已填补",         "method": "state_marker"},
        {"id": "intel_summary_written", "desc": "intel-summary.md 已创建", "method": "file_check", "path": ".sisyphus/logs/{task}/intel-summary.md"},
    ],
    "P2": [
        {"id": "plan_file_exists",     "desc": "计划文件已创建",          "method": "file_check", "path": ".sisyphus/plans/{task}.md"},
        {"id": "momus_0_blocker",      "desc": "@momus 审查 0 BLOCKER",  "method": "state_marker"},
        {"id": "oracle_plan_approved", "desc": "@oracle 方案审查通过",    "method": "state_marker"},
        {"id": "user_plan_confirmed",  "desc": "用户已确认计划",          "method": "state_marker"},
    ],
    "P3": [
        {"id": "draft_complete",        "desc": "初稿撰写完毕",           "method": "state_marker"},
        {"id": "oracle_0_blocker",      "desc": "@oracle 审核 0 BLOCKER", "method": "state_marker"},
        {"id": "oracle_rating_B_plus",  "desc": "评级 ≥ B",              "method": "state_marker"},
        {"id": "user_design_confirmed", "desc": "用户已确认方案",          "method": "state_marker"},
    ],
    "P4": [
        {"id": "conventions_created",    "desc": "PROJECT_CONVENTIONS.md 已创建",       "method": "file_check", "path": "PROJECT_CONVENTIONS.md"},
        {"id": "doctrine_frozen",        "desc": "IMPLEMENTATION_DOCTRINE.md 已冻结",   "method": "file_check", "path": "IMPLEMENTATION_DOCTRINE.md"},
        {"id": "mapping_table_done",     "desc": "业务-工程映射表已完成",                "method": "state_marker"},
        {"id": "sync_initialized",       "desc": ".sisyphus/sync/ 已初始化",            "method": "dir_check",  "path": ".sisyphus/sync/"},
        {"id": "phase_summary_written",  "desc": "phase-4-summary.md 已创建",           "method": "file_check", "path": ".sisyphus/sync/phase-4-summary.md"},
    ],
    "P5": [
        {"id": "schema_executable",     "desc": "Migration up/down 通过",     "method": "state_marker"},
        {"id": "api_contract_complete", "desc": "所有端点+状态码已定义",       "method": "state_marker"},
        {"id": "types_generated",       "desc": "共享类型已自动生成且幂等",    "method": "state_marker"},
        {"id": "contracts_md_created",  "desc": "CONTRACTS.md 已创建",        "method": "file_check", "path": "CONTRACTS.md"},
        {"id": "contract_locked",       "desc": "contract-status.md 已初始化", "method": "file_check", "path": ".sisyphus/sync/contract-status.md"},
    ],
    "P6A": [
        {"id": "all_endpoints_implemented", "desc": "所有契约端点已实现",         "method": "state_marker"},
        {"id": "backend_build_pass",        "desc": "全量构建通过",              "method": "state_marker"},
        {"id": "backend_tests_pass",        "desc": "全量测试通过",              "method": "state_marker"},
        {"id": "backend_types_pass",        "desc": "类型检查通过",              "method": "state_marker"},
        {"id": "doctrine_backend_gate",     "desc": "DOCTRINE 后端 Gate 全部通过", "method": "state_marker"},
        {"id": "backend_progress_complete", "desc": "backend-progress.md 全 completed", "method": "content_check", "path": ".sisyphus/sync/backend-progress.md", "contains": "completed"},
    ],
    "P6B": [
        {"id": "all_pages_rendered",         "desc": "所有页面可渲染+交互正常",      "method": "state_marker"},
        {"id": "frontend_build_pass",        "desc": "全量构建通过",                "method": "state_marker"},
        {"id": "frontend_tests_pass",        "desc": "全量测试通过",                "method": "state_marker"},
        {"id": "frontend_types_pass",        "desc": "类型检查通过",                "method": "state_marker"},
        {"id": "doctrine_frontend_gate",     "desc": "DOCTRINE 前端 Gate 全部通过",  "method": "state_marker"},
        {"id": "frontend_progress_complete", "desc": "frontend-progress.md 全 completed", "method": "content_check", "path": ".sisyphus/sync/frontend-progress.md", "contains": "completed"},
    ],
    "P7": [
        {"id": "smoke_test_pass",         "desc": "契约验证+Mock清除+构建通过",  "method": "state_marker"},
        {"id": "e2e_pass",                "desc": "端到端联调通过",              "method": "state_marker"},
        {"id": "data_roundtrip_verified", "desc": "数据往返验证通过",            "method": "state_marker"},
        {"id": "security_scan_pass",      "desc": "安全验证通过",                "method": "state_marker"},
    ],
    "P8": [
        {"id": "self_verify_pass",       "desc": "自我迭代验证通过",              "method": "state_marker"},
        {"id": "oracle_final_pass",      "desc": "@oracle 最终架构审查全通过",  "method": "state_marker"},
        {"id": "consistency_scan_pass",  "desc": "全量一致性扫描通过",          "method": "state_marker"},
        {"id": "user_accepted",          "desc": "用户确认验收",                "method": "state_marker"},
    ],
}

# ─── 模式 → 阶段管线 ───
MODE_PIPELINES = {
    "fullstack":        ["P0", "P1", "P2", "P4", "P5", "P6A", "P6B", "P7", "P8"],
    "fullstack+design": ["P0", "P1", "P2", "P3", "P4", "P5", "P6A", "P6B", "P7", "P8"],
    "standard":         ["P0", "P1", "P2", "P4", "P6A", "P6B", "P7", "P8"],
    "backend":          ["P0", "P1", "P2", "P4", "P5", "P6A", "P8"],
    "frontend":         ["P0", "P1", "P2", "P4", "P5", "P6B", "P8"],
    "database":         ["P0", "P1", "P2", "P4", "P5", "P8"],
    "design":           ["P0", "P1", "P2", "P3", "P8"],
    "simple":           ["P0", "P1", "P2", "P8"],
    "review":           ["P0", "P1", "P7", "P8"],
}

GATE_REVIEWER_ALLOWLIST = ("oracle", "momus")

ACTIVE_RUN_FILE = "ACTIVE_RUN"


def find_sisyphus_root(start_dir=None):
    """从 start_dir 向上搜索 .sisyphus 根目录，返回路径或 None。"""
    d = Path(start_dir or os.getcwd()).resolve()
    while True:
        sisy_dir = d / ".sisyphus"
        if sisy_dir.is_dir():
            return str(sisy_dir)
        parent = d.parent
        if parent == d:
            return None
        d = parent


def read_active_run_id(sisy_root):
    """读取 ACTIVE_RUN 文件，失败时返回空字符串。"""
    if not sisy_root:
        return ""

    active_run_file = Path(sisy_root) / ACTIVE_RUN_FILE
    if not active_run_file.is_file():
        return ""

    try:
        return active_run_file.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def get_run_state_path(sisy_root, run_id):
    """返回指定 run_id 对应的 state.json 路径，不存在则返回 None。"""
    if not sisy_root or not run_id:
        return None

    run_state = Path(sisy_root) / "runs" / run_id / "state.json"
    if run_state.is_file():
        return str(run_state)
    return None

# ─── 阶段 → 步骤列表 ───
PHASE_STEPS = {
    "P0":  [("triage",              "P0-triage.md")],
    "P1":  [("metis-intent",        "P1-metis-intent.md"),
            ("explore-intel",       "P1-explore-intel.md"),
            ("librarian-intel",     "P1-librarian-intel.md")],
    "P2":  [("prometheus-plan",     "P2-prometheus-plan.md"),
            ("momus-review",        "P2-momus-review.md"),
            ("oracle-plan-review",  "P2-oracle-plan-review.md")],
    "P3":  [("hephaestus-design",   "P3-hephaestus-design.md"),
            ("oracle-design-review","P3-oracle-design-review.md"),
            ("oracle-review-classify","P3-oracle-review-classify.md")],
    "P4":  [("conventions",         "P4-conventions.md"),
            ("doctrine",            "P4-doctrine.md"),
            ("mapping",             "P4-mapping-table.md")],
    "P5":  [("contract-schema",     "P5-contract-schema.md"),
            ("contract-api",        "P5-contract-api.md"),
            ("contract-types",      "P5-contract-types.md")],
    "P6A": [("B1-scaffold",         "P6A-backend-B1-scaffold.md"),
            ("B2-migration",        "P6A-backend-B2-migration.md"),
            ("B3-data-access",      "P6A-backend-B3-data-access.md"),
            ("B4-feature",          "P6A-backend-B4-feature.md"),
            ("B5-middleware",        "P6A-backend-B5-middleware.md"),
            ("B6-security",         "P6A-backend-B6-security.md"),
            ("B7-observability",    "P6A-backend-B7-observability.md"),
            ("B8-test",             "P6A-backend-B8-test.md")],
    "P6B": [("F1-scaffold",         "P6B-frontend-F1-scaffold.md"),
            ("F2-data-layer",       "P6B-frontend-F2-data-layer.md"),
            ("F3-mock",             "P6B-frontend-F3-mock.md"),
            ("F4-components",       "P6B-frontend-F4-components.md"),
            ("F5-pages",            "P6B-frontend-F5-pages.md"),
            ("F6-interaction",      "P6B-frontend-F6-interaction.md"),
            ("F7-quality",          "P6B-frontend-F7-quality.md")],
    "P7":  [("smoke",               "P7-integration-smoke.md"),
            ("e2e",                 "P7-integration-e2e.md"),
            ("security-validation", "P7-security-validation.md")],
    "P8":  [("self-verify",          "P8-self-verify.md"),
            ("oracle-final",        "P8-oracle-final.md"),
            ("delivery",            "P8-delivery-summary.md")],
}

# ─── 步骤分组（并行可见性控制） ───
# 每个阶段是 list[list[step_name]]，内层 list 为一个"组"。
# 组内步骤同时输出给 AI，组间顺序执行。
STEP_GROUPS = {
    "P0":  [["triage"]],
    "P1":  [["metis-intent"], ["explore-intel", "librarian-intel"]],
    "P2":  [["prometheus-plan"], ["momus-review", "oracle-plan-review"]],
    "P3":  [["hephaestus-design"], ["oracle-design-review"], ["oracle-review-classify"]],
    "P4":  [["conventions", "doctrine", "mapping"]],
    "P5":  [["contract-schema"], ["contract-api"], ["contract-types"]],
    "P6A": [["B1-scaffold"], ["B2-migration"], ["B3-data-access"], ["B4-feature"],
            ["B5-middleware"], ["B6-security"], ["B7-observability"], ["B8-test"]],
    "P6B": [["F1-scaffold"], ["F2-data-layer"], ["F3-mock"], ["F4-components"],
            ["F5-pages"], ["F6-interaction"], ["F7-quality"]],
    "P7":  [["smoke"], ["e2e", "security-validation"]],
    "P8":  [["self-verify"], ["oracle-final"], ["delivery"]],
}

# 横切模板（值为 (文件名, section_key) 元组）
CROSS_CUTTING_TEMPLATES = {
    "blocking-resolution": ("X.md", "blocking-resolution"),
    "amendment-protocol":  ("X.md", "amendment-protocol"),
    "work-logs":           ("X.md", "work-logs"),
    "oracle-consult":      ("X.md", "oracle-consult"),
}

# ─── Phase 级模板映射 ───
PHASE_TEMPLATE = {
    "P0": "P0.md",
    "P1": "P1.md",
    "P2": "P2.md",
    "P3": "P3.md",
    "P4": "P4.md",
    "P5": "P5.md",
    "P6A": "P6A.md",
    "P6B": "P6B.md",
    "P7": "P7.md",
    "P8": "P8.md",
}

# ─── 路径工具 ───

def find_state(start_dir=None, run_id=None):
    """从 start_dir 向上搜索 state.json，支持显式 run_id 指定。"""
    d = Path(start_dir or os.getcwd()).resolve()
    while True:
        sisy_dir = d / ".sisyphus"
        if sisy_dir.is_dir():
            if run_id:
                run_state = get_run_state_path(str(sisy_dir), run_id)
                if run_state:
                    return run_state
            else:
                active_run_id = read_active_run_id(str(sisy_dir))
                if active_run_id:
                    run_state = get_run_state_path(str(sisy_dir), active_run_id)
                    if run_state:
                        return run_state

                candidate = sisy_dir / "state.json"
                if candidate.is_file():
                    return str(candidate)

                runs_dir = sisy_dir / "runs"
                if runs_dir.is_dir():
                    run_states = [p / "state.json" for p in runs_dir.iterdir() if p.is_dir() and (p / "state.json").is_file()]
                    if run_states:
                        latest = max(run_states, key=lambda p: p.stat().st_mtime)
                        return str(latest)

        parent = d.parent
        if parent == d:
            return None
        d = parent


def get_sisyphus_root(state_path):
    """从 state.json 路径推导 .sisyphus 根目录。"""
    p = Path(state_path).resolve()
    for cur in [p.parent, *p.parents]:
        if cur.name == ".sisyphus":
            return str(cur)
    return str(p.parent)


def get_run_root(state_path):
    """从 state.json 路径推导当前 run 根目录。"""
    p = Path(state_path).resolve()
    if p.parent.parent.name == "runs":
        return str(p.parent)
    return get_sisyphus_root(state_path)


def get_project_root(state_path):
    """从 state.json 路径推导项目根目录。"""
    sisy_root = Path(get_sisyphus_root(state_path)).resolve()
    return str(sisy_root.parent)


def get_run_context(state_path, state):
    """构建运行上下文摘要，供只读查看命令展示。"""
    sisy_root = get_sisyphus_root(state_path)
    active_run_id = read_active_run_id(sisy_root)
    target_run_id = state.get("run_id") or Path(get_run_root(state_path)).name

    return {
        "target_run_id": target_run_id or "—",
        "task_name": state.get("task_name", "—"),
        "active_run_id": active_run_id or "未设置",
        "is_active_run": bool(target_run_id) and target_run_id == active_run_id,
    }


def run_context_pairs(state_path, state):
    """将运行上下文转换为 Markdown kv 对。"""
    context = get_run_context(state_path, state)
    return [
        ("目标 run-id", context["target_run_id"]),
        ("task_name", context["task_name"]),
        ("是否 ACTIVE_RUN", "是" if context["is_active_run"] else "否"),
        ("当前 ACTIVE_RUN", context["active_run_id"]),
    ]


def get_run_root_rel(state_path):
    """返回当前 run 根目录相对项目根路径。"""
    project_root = Path(get_project_root(state_path)).resolve()
    run_root = Path(get_run_root(state_path)).resolve()
    rel = os.path.relpath(str(run_root), str(project_root))
    return rel.replace("\\", "/")


def map_sisyphus_path(path, state):
    """将 .sisyphus/* 路径映射到当前 run 根目录下。"""
    normalized = path.replace("\\", "/")
    if not normalized.startswith(".sisyphus/"):
        return normalized

    run_root = (state.get("run_root") or ".sisyphus").replace("\\", "/").rstrip("/")
    if run_root == ".sisyphus":
        return normalized

    suffix = normalized[len(".sisyphus/"):]
    return f"{run_root}/{suffix}"


def get_skill_root():
    """获取 dev-orchestration SKILL 根目录（scripts/ 的父目录）。"""
    return str(Path(__file__).parent.parent)


def get_template_path(template_name):
    """获取 dispatch 模板的绝对路径。"""
    return str(Path(get_skill_root()) / "data" / "templates" / template_name)


# ─── 状态读写 ───

def load_state(state_path):
    """加载 state.json，返回 dict。"""
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state_path, state):
    """保存 state.json。"""
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def now_iso():
    """返回当前时间 ISO 格式字符串。"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ─── Markdown 渲染工具 ───

def md_heading(text, level=2):
    return "#" * level + " " + text


def md_table(headers, rows):
    """渲染 Markdown 表格。headers: list[str], rows: list[list[str]]。"""
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def md_kv(pairs):
    """渲染 key-value 列表。pairs: list[tuple[str, str]]。"""
    return "\n".join(f"- **{k}**: {v}" for k, v in pairs)


def gate_status_icon(status):
    icons = {"passed": "✅", "skipped": "⏭️", "failed": "❌", "pending": "⏳"}
    return icons.get(status, "❓")


def pipeline_str(pipeline):
    return " → ".join(pipeline)


def resolve_review_path(project_root, review_path):
    """将 review 路径解析为绝对路径（相对路径按项目根目录解析）。"""
    if not review_path:
        return ""
    if os.path.isabs(review_path):
        return os.path.normpath(review_path)
    return os.path.normpath(os.path.join(project_root, review_path))


def _extract_review_field(content, field_name):
    """提取 review 证据字段值，找不到返回空字符串。"""
    pattern = rf"(?m)^\s*{re.escape(field_name)}\s*:\s*(.*?)\s*$"
    match = re.search(pattern, content)
    if not match:
        return ""
    return match.group(1).strip()


def _is_placeholder_value(value):
    """判断字段值是否为占位文本。"""
    normalized = re.sub(r"\s+", "", value).lower()
    return normalized in {"...", "tbd", "todo", "n/a", "na", "-", "待补充"}


def validate_gate_review_evidence(project_root, review_path, phase, gate_id):
    """校验 gate review 证据文件格式与内容，返回 (ok, detail)。"""
    if not review_path:
        return False, "缺少 review 证据路径（reason）"

    full_path = resolve_review_path(project_root, review_path)
    if not os.path.isfile(full_path):
        return False, f"review 证据文件不存在: {review_path}"

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"无法读取 review 证据文件: {e}"

    gate_value = _extract_review_field(content, "Gate")
    if not gate_value:
        return False, "缺少字段 Gate:"

    expected_gate = f"{phase}/{gate_id}"
    if gate_value != expected_gate:
        return False, f"Gate 值必须为 {expected_gate}"

    reviewer = _extract_review_field(content, "Reviewer")
    if not reviewer:
        return False, "缺少字段 Reviewer:"
    if reviewer.lower() not in GATE_REVIEWER_ALLOWLIST:
        allowed = ", ".join(GATE_REVIEWER_ALLOWLIST)
        return False, f"Reviewer 必须为以下之一: {allowed}"

    scope = _extract_review_field(content, "Scope")
    if not scope:
        return False, "缺少字段 Scope:"
    if not re.search(r"(dependency-impact|依赖影响)", scope, re.IGNORECASE):
        return False, "字段 Scope 必须体现 dependency-impact/依赖影响"

    upstream = _extract_review_field(content, "Upstream-Dependencies")
    if not upstream:
        return False, "缺少字段 Upstream-Dependencies:"
    if _is_placeholder_value(upstream):
        return False, "字段 Upstream-Dependencies 不能为占位值"

    downstream = _extract_review_field(content, "Downstream-Dependencies")
    if not downstream:
        return False, "缺少字段 Downstream-Dependencies:"
    if _is_placeholder_value(downstream):
        return False, "字段 Downstream-Dependencies 不能为占位值"

    verdict = _extract_review_field(content, "Verdict")
    if verdict != "PASS":
        return False, "缺少字段 Verdict: PASS"

    return True, f"review 证据有效: {review_path}"


# ─── 门控验证工具 ───

def verify_gate(gate_def, state, project_root):
    """验证单个门控，返回 (status, detail)。"""
    task = state.get("task_name", "unknown")
    method = gate_def["method"]
    gate_id = gate_def["id"]
    phase = None
    for p, gates in PHASE_GATES.items():
        if any(g["id"] == gate_id for g in gates):
            phase = p
            break

    # 先检查 state 中的标记
    if phase:
        phase_data = state.get("phases", {}).get(phase, {})
        gate_state = phase_data.get("gates", {}).get(gate_id, {})
        marked_status = gate_state.get("status")
        if marked_status == "passed":
            review_path = gate_state.get("reason", "")
            ok, detail = validate_gate_review_evidence(project_root, review_path, phase, gate_id)
            if ok:
                return "passed", review_path
            return "pending", detail
        if marked_status == "skipped":
            return marked_status, gate_state.get("reason", "")

    if method == "state_marker":
        return "pending", "未标记"

    if method == "file_check":
        raw_path = gate_def["path"].replace("{task}", task)
        path = map_sisyphus_path(raw_path, state)
        full_path = os.path.join(project_root, path)
        if os.path.isfile(full_path):
            return "passed", f"{path} 存在"
        return "pending", f"{path} 不存在"

    if method == "dir_check":
        raw_path = gate_def["path"].replace("{task}", task)
        path = map_sisyphus_path(raw_path, state)
        full_path = os.path.join(project_root, path)
        if os.path.isdir(full_path):
            return "passed", f"{path} 存在"
        return "pending", f"{path} 不存在"

    if method == "content_check":
        raw_path = gate_def["path"].replace("{task}", task)
        path = map_sisyphus_path(raw_path, state)
        full_path = os.path.join(project_root, path)
        contains = gate_def.get("contains", "")
        if os.path.isfile(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            if contains and contains in content:
                return "passed", f"包含 '{contains}'"
            return "pending", f"不包含 '{contains}'"
        return "pending", f"{path} 不存在"

    return "pending", f"未知验证方法: {method}"


def find_next_pending_step(phase, state):
    """在给定阶段中找到第一个尚未完成的步骤。"""
    steps = PHASE_STEPS.get(phase, [])
    completed_steps = state.get("phases", {}).get(phase, {}).get("completed_steps", [])
    for step_name, template in steps:
        if step_name not in completed_steps:
            return step_name, template
    return None, None


def find_next_pending_group(phase, state):
    """在给定阶段中找到下一个未完成的步骤组。

    返回 (pending_steps: list[tuple[step_name, template]], is_parallel: bool)。
    pending_steps 只包含组内尚未完成的步骤。
    is_parallel 表示该组原本包含多个步骤（并行组）。
    如果全部完成，返回 ([], False)。
    """
    groups = STEP_GROUPS.get(phase, [])
    completed_steps = state.get("phases", {}).get(phase, {}).get("completed_steps", [])
    step_map = dict(PHASE_STEPS.get(phase, []))

    for group in groups:
        pending = [(s, step_map[s]) for s in group if s not in completed_steps]
        if pending:
            return pending, len(group) > 1
    return [], False
