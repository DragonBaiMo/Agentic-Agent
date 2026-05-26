#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
  cat <<'EOF'
Agentic Agent installer

Build and distribute this repo's Agent/Skill artifacts into local agent config
directories.

Usage:
  scripts/install-agent-config.sh [options]

Options:
  --target <name...>       Platforms to build/distribute. Default: all
                           Known targets: copilot, codex, windsurf, opencode, kimicode
  --platform <name>        Source rewrite profile. Default: auto
                           Known profiles: auto, macos, linux, windows
  --mode <replace|merge>   Distribution mode. Default: replace
  --project <path>         Also install Copilot agents/skills into <path>/.github/
  --no-build               Distribute existing build output without rebuilding
  --dry-run                Print planned actions only
  --yes                    Skip confirmation prompt
  --help                   Show this help

Examples:
  scripts/install-agent-config.sh --dry-run
  scripts/install-agent-config.sh --target copilot --dry-run
  scripts/install-agent-config.sh --target copilot --project /path/to/repo
  scripts/install-agent-config.sh --target codex opencode --mode merge
EOF
}

TARGETS=()
PLATFORM="auto"
MODE="replace"
PROJECT_PATH=""
NO_BUILD=0
DRY_RUN=0
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        TARGETS+=("$1")
        shift
      done
      ;;
    --platform)
      [[ $# -ge 2 ]] || { echo "[error] --platform requires a value" >&2; exit 2; }
      PLATFORM="$2"
      shift 2
      ;;
    --mode)
      [[ $# -ge 2 ]] || { echo "[error] --mode requires a value" >&2; exit 2; }
      MODE="$2"
      shift 2
      ;;
    --project|--copilot-project)
      [[ $# -ge 2 ]] || { echo "[error] --project requires a path" >&2; exit 2; }
      PROJECT_PATH="$2"
      shift 2
      ;;
    --no-build)
      NO_BUILD=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --yes|-y)
      ASSUME_YES=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$MODE" != "replace" && "$MODE" != "merge" ]]; then
  echo "[error] --mode must be replace or merge" >&2
  exit 2
fi

case "$PLATFORM" in
  auto|macos|linux|windows) ;;
  *)
    echo "[error] --platform must be auto, macos, linux, or windows" >&2
    exit 2
    ;;
esac

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[error] Python not found: $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN=/path/to/python3 or install Python 3." >&2
  exit 127
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=("all")
fi

cd "$ROOT_DIR"

echo "Agentic Agent installer"
echo "Repository: $ROOT_DIR"
echo "Python: $("$PYTHON_BIN" --version 2>&1)"
echo "Targets: ${TARGETS[*]}"
echo "Source platform profile: $PLATFORM"
echo "Mode: $MODE"
if [[ -n "$PROJECT_PATH" ]]; then
  echo "Copilot project install: $PROJECT_PATH/.github/{agents,skills}"
fi
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run: yes"
fi

echo
echo "Step 1/3: build artifacts"
if [[ "$NO_BUILD" -eq 1 ]]; then
  echo "Skipping build because --no-build was provided."
else
  "$PYTHON_BIN" scripts/build.py --target "${TARGETS[@]}" --platform "$PLATFORM"
fi

echo
echo "Step 2/3: preview distribution"
preview_cmd=(
  "$PYTHON_BIN" scripts/distribute.py
  --target "${TARGETS[@]}"
  --mode "$MODE"
  --no-build
  --dry-run
  --platform "$PLATFORM"
)
if [[ -n "$PROJECT_PATH" ]]; then
  preview_cmd+=(--copilot-project "$PROJECT_PATH")
fi
"${preview_cmd[@]}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo
  echo "Step 3/3: stopped after dry-run. No files were written."
  exit 0
fi

if [[ "$ASSUME_YES" -ne 1 ]]; then
  echo
  read -r -p "Apply the distribution above? [y/N] " reply
  case "$reply" in
    y|Y|yes|YES) ;;
    *)
      echo "Aborted. No distribution was applied."
      exit 0
      ;;
  esac
fi

echo
echo "Step 3/3: distribute artifacts"
apply_cmd=(
  "$PYTHON_BIN" scripts/distribute.py
  --target "${TARGETS[@]}"
  --mode "$MODE"
  --no-build
  --platform "$PLATFORM"
)
if [[ -n "$PROJECT_PATH" ]]; then
  apply_cmd+=(--copilot-project "$PROJECT_PATH")
fi
"${apply_cmd[@]}"

echo
echo "Done."
