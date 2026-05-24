"""E2E 全链路测试"""
import sys, os, tempfile, shutil
import io
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dev-orchestration', 'scripts'))

from cli import main as cli_main
from state import cmd_init, cmd_done, cmd_mark, cmd_advance
from gate import cmd_gate
from dispatch import cmd_dispatch, cmd_dispatch_phase
from router import cmd_route
from core import load_state, save_state, find_state


RUN_ROOT_REL = ".sisyphus"


def _to_os_path(rel_path):
    return rel_path.replace("/", os.sep)


def write_review(phase, gate_id):
    """写入最小可用 gate 二审证据文件，返回相对路径。"""
    rel_path = f"{RUN_ROOT_REL}/reviews/{phase}-{gate_id}.md"
    abs_path = os.path.join(os.getcwd(), _to_os_path(rel_path))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(
            f"Gate: {phase}/{gate_id}\n"
            "Reviewer: oracle\n"
            "Scope: dependency-impact e2e lifecycle sanity check\n"
            "Upstream-Dependencies: state initialization\n"
            "Downstream-Dependencies: gate auto-advance\n"
            "Verdict: PASS\n"
        )
    return rel_path


def write_custom_review(
    filename,
    gate_value,
    verdict,
    reviewer="oracle",
    scope="dependency-impact e2e lifecycle sanity check",
    upstream="state initialization",
    downstream="gate auto-advance",
):
    """写入可控字段的 gate 二审证据文件，返回相对路径。"""
    rel_path = f"{RUN_ROOT_REL}/reviews/{filename}.md"
    abs_path = os.path.join(os.getcwd(), _to_os_path(rel_path))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(
            f"Gate: {gate_value}\n"
            f"Reviewer: {reviewer}\n"
            f"Scope: {scope}\n"
            f"Upstream-Dependencies: {upstream}\n"
            f"Downstream-Dependencies: {downstream}\n"
            f"Verdict: {verdict}\n"
        )
    return rel_path


def expect_system_exit(case_name, fn):
    try:
        fn()
    except SystemExit as e:
        assert e.code != 0, f"{case_name}: expected non-zero SystemExit code"
        print(f"PASS: {case_name}")
        return
    raise AssertionError(f"{case_name}: expected SystemExit")


def run_cli(args):
    old_argv = sys.argv[:]
    buffer = io.StringIO()
    try:
        sys.argv = ["dev-orch", *args]
        with redirect_stdout(buffer):
            cli_main()
    finally:
        sys.argv = old_argv

    output = buffer.getvalue()
    print(output)
    return output

tmpdir = tempfile.mkdtemp()
os.chdir(tmpdir)

print("=" * 60)
print("E2E TEST: fullstack mode lifecycle")
print("=" * 60)

# 1. Init
cmd_init("fullstack", "e2e-test")
state_path = find_state(tmpdir)
assert state_path, "Expected active state after init"
state = load_state(state_path)
first_run_id = state["run_id"]
RUN_ROOT_REL = state.get("run_root", ".sisyphus")
print()

# 2. Route
print("--- route ---")
cmd_route()
print()

# 3. Dispatch P0 (phase-level)
print("--- dispatch P0 (phase) ---")
cmd_dispatch_phase("P0")
print()

# 4. Done + Mark P0
cmd_done("P0", ["triage"])
decision_dir = os.path.join(tmpdir, _to_os_path(f"{RUN_ROOT_REL}/logs/e2e-test"))
os.makedirs(decision_dir, exist_ok=True)
with open(os.path.join(decision_dir, "decision.md"), "w", encoding="utf-8") as f:
    f.write("test decision")

expect_system_exit(
    "cmd_mark passed without review path is rejected",
    lambda: cmd_mark("P0", "path_selected", "passed"),
)

bad_gate_review = write_custom_review(
    "P0-path_selected-bad-gate",
    "P0/path_selected-extra",
    "PASS",
)
expect_system_exit(
    "cmd_mark rejects review with mismatched Gate",
    lambda: cmd_mark("P0", "path_selected", "passed", bad_gate_review),
)

bad_verdict_review = write_custom_review(
    "P0-path_selected-bad-verdict",
    "P0/path_selected",
    "FAIL",
)
expect_system_exit(
    "cmd_mark rejects review with non-PASS Verdict",
    lambda: cmd_mark("P0", "path_selected", "passed", bad_verdict_review),
)

bad_reviewer_review = write_custom_review(
    "P0-path_selected-bad-reviewer",
    "P0/path_selected",
    "PASS",
    reviewer="hephaestus",
)
expect_system_exit(
    "cmd_mark rejects review with non-allowlisted Reviewer",
    lambda: cmd_mark("P0", "path_selected", "passed", bad_reviewer_review),
)

bad_scope_review = write_custom_review(
    "P0-path_selected-bad-scope",
    "P0/path_selected",
    "PASS",
    scope="e2e lifecycle sanity check",
)
expect_system_exit(
    "cmd_mark rejects review without dependency-impact semantics in Scope",
    lambda: cmd_mark("P0", "path_selected", "passed", bad_scope_review),
)

bad_upstream_placeholder_review = write_custom_review(
    "P0-path_selected-bad-upstream-placeholder",
    "P0/path_selected",
    "PASS",
    upstream="TBD",
)
expect_system_exit(
    "cmd_mark rejects review with placeholder Upstream-Dependencies",
    lambda: cmd_mark("P0", "path_selected", "passed", bad_upstream_placeholder_review),
)

cmd_mark("P0", "path_selected", "passed", write_review("P0", "path_selected"))
cmd_mark("P0", "decision_logged", "passed", write_review("P0", "decision_logged"))
print()

# 5. Gate with auto-advance
print("--- gate P0 --auto-advance ---")
cmd_gate("P0", auto_advance=True)
print()

# 6. Verify we're in P1
state = load_state(state_path)
assert state["current_phase"] == "P1", "Expected P1 after auto-advance"
print("PASS: Auto-advanced to P1")
print()

# 7. Dispatch P1 (phase-level)
print("--- dispatch P1 (phase) ---")
cmd_dispatch_phase("P1")
print()

# 8. Done metis-intent, then dispatch P1 again
cmd_done("P1", ["metis-intent"])
print()
print("--- dispatch P1 after metis-intent done ---")
cmd_dispatch_phase("P1")
print()

# 9. Done group 2
cmd_done("P1", ["explore-intel", "librarian-intel"])
print()

# 10. Verify P1 dispatch shows all done
print("--- dispatch P1 (all done) ---")
cmd_dispatch_phase("P1")
print()

# 11. Single step dispatch (backward compat / degraded)
state = load_state(state_path)
state["current_phase"] = "P2"
state["current_phase_index"] = 2
state["phases"]["P1"]["status"] = "completed"
state["phases"]["P2"]["status"] = "in_progress"
save_state(state_path, state)

print("--- dispatch P2 prometheus-plan (compat) ---")
cmd_dispatch("P2", "prometheus-plan")
print()

# 12. Multi-run init should keep history and switch ACTIVE_RUN
first_state_path = state_path
cmd_init("simple", "e2e-second")
state_path = find_state(tmpdir)
assert state_path and state_path != first_state_path, "Expected ACTIVE_RUN to point to newest run"
state = load_state(state_path)
second_run_id = state["run_id"]
assert state["task_name"] == "e2e-second", "Expected second run to become ACTIVE_RUN"
print("PASS: init creates independent run and keeps old run history")

from state import cmd_history
print("--- history ---")
cmd_history()
print()

# 13. Read-only inspect an older run via CLI --run-id
print("--- current --run-id first run ---")
current_output = run_cli(["current", "--run-id", first_run_id])
assert first_run_id in current_output, "Expected current --run-id to show target run-id"
assert second_run_id in current_output, "Expected current --run-id to show ACTIVE_RUN context"
assert "e2e-test" in current_output, "Expected current --run-id to show target task_name"
assert "是否 ACTIVE_RUN" in current_output, "Expected current --run-id to show active marker"
print("PASS: current --run-id reads non-active run")
print()

print("--- route --run-id first run --verbose ---")
route_output = run_cli(["route", "--run-id", first_run_id, "--verbose"])
assert "上下文恢复报告" in route_output, "Expected verbose route output"
assert first_run_id in route_output, "Expected route --run-id to show target run-id"
assert "e2e-test" in route_output, "Expected route --run-id to show target task_name"
print("PASS: route --run-id reads non-active run")
print()

print("--- dispatch P1 --run-id first run ---")
dispatch_output = run_cli(["dispatch", "P1", "--run-id", first_run_id])
assert "调度预览上下文" in dispatch_output, "Expected dispatch preview context"
assert "只读预览" in dispatch_output, "Expected dispatch --run-id to emphasize read-only preview"
assert first_run_id in dispatch_output, "Expected dispatch --run-id to show target run-id"
print("PASS: dispatch <phase> --run-id previews non-active run")
print()

print("--- dispatch --cross work-logs --run-id first run ---")
cross_output = run_cli(["dispatch", "--cross", "work-logs", "--run-id", first_run_id])
assert "调度预览上下文" in cross_output, "Expected cross dispatch preview context"
assert "只读预览" in cross_output, "Expected cross dispatch --run-id to emphasize read-only preview"
assert first_run_id in cross_output, "Expected cross dispatch --run-id to show target run-id"
print("PASS: dispatch --cross --run-id previews non-active run")
print()

print("--- history --task SECOND ---")
history_filter_output = run_cli(["history", "--task", "SECOND"])
assert "e2e-second" in history_filter_output, "Expected history --task to keep matching task"
assert "e2e-test" not in history_filter_output, "Expected history --task to filter out non-matching task"
print("PASS: history --task filters task_name case-insensitively")
print()

# 14. Compile check all scripts
import py_compile
scripts_dir = os.path.dirname(os.path.abspath(__file__))
for f in ["core.py", "cli.py", "state.py", "router.py", "dispatch.py", "gate.py"]:
    py_compile.compile(os.path.join(scripts_dir, f), doraise=True)
print("PASS: All 6 scripts compile OK")

print()
print("=" * 60)
print("ALL E2E TESTS PASSED")
print("=" * 60)

os.chdir(os.path.join(os.path.dirname(__file__), ".."))
shutil.rmtree(tmpdir, ignore_errors=True)