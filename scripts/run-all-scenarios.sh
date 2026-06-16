#!/usr/bin/env bash
# Run every ChatVis scenario against its expected dataset.
#
# Usage:
#   scripts/run-all-scenarios.sh <anl-username> [extra chatvis flags ...]
#
# Examples:
#   scripts/run-all-scenarios.sh jdoe
#   scripts/run-all-scenarios.sh jdoe --log-level debug --max-repair-attempts 10
#   scripts/run-all-scenarios.sh jdoe --pvpython /opt/paraview/bin/pvpython
#
# Outputs:
#   out/<scenario>.png         - generated screenshot
#   out/<scenario>.py          - generated ParaView script (sibling, written by chatvis)
#   out/<scenario>.log         - captured stdout+stderr of the chatvis invocation
#
# Behavior:
#   - Runs all five scenarios regardless of individual failures.
#   - Prints a pass/fail summary table at the end.
#   - Exits 0 only if every scenario exited 0.

set -u  # NB: not -e; we want to continue past failed scenarios.

# Resolve the repo root from the script's own location so the script
# can be invoked from any cwd.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <anl-username> [extra chatvis flags ...]" >&2
    exit 2
fi

USERNAME="$1"
shift
EXTRA_ARGS=("$@")

DATA_DIR="${REPO_ROOT}/data"
OUT_DIR="${REPO_ROOT}/out"
mkdir -p "${OUT_DIR}"

# Scenario -> dataset basename. Must mirror chatvis/main.py's
# _EXPECTED_DATA_BY_SCENARIO; if these drift, chatvis will warn at
# runtime but still proceed.
declare -A DATASET=(
    [ml-dvr]="ml-100.vti"
    [ml-iso]="ml-100.vti"
    [ml-slice-iso]="ml-100.vti"
    [points-surf-clip]="can_points.ex2"
    [stream-glyph]="disk.ex2"
)

# Preserve insertion order via an explicit list (associative arrays
# have no defined iteration order in bash).
SCENARIOS=(
    ml-dvr
    ml-iso
    ml-slice-iso
    points-surf-clip
    stream-glyph
)

declare -A RESULT  # scenario -> "PASS" | "FAIL (exit N)"

for scenario in "${SCENARIOS[@]}"; do
    data_file="${DATA_DIR}/${DATASET[$scenario]}"
    screenshot_path="${OUT_DIR}/${scenario}.png"
    log_path="${OUT_DIR}/${scenario}.log"

    echo
    echo "================================================================"
    echo "Scenario: ${scenario}"
    echo "  data:       ${data_file}"
    echo "  screenshot: ${screenshot_path}"
    echo "  log:        ${log_path}"
    echo "================================================================"

    if [[ ! -f "${data_file}" ]]; then
        echo "SKIP: dataset not found at ${data_file}"
        RESULT[$scenario]="FAIL (missing dataset)"
        continue
    fi

    # Tee chatvis output to both the terminal and the per-scenario log
    # so a watcher sees progress live and a post-mortem reader has the
    # full transcript on disk.
    (
        cd "${REPO_ROOT}" && \
        uv run python -m chatvis.main \
            --scenario "${scenario}" \
            --data-filepath "${data_file}" \
            --screenshot-path "${screenshot_path}" \
            --username "${USERNAME}" \
            "${EXTRA_ARGS[@]}"
    ) 2>&1 | tee "${log_path}"
    # PIPESTATUS[0] is chatvis's exit code; $? is tee's (always 0 here).
    exit_code="${PIPESTATUS[0]}"

    if [[ "${exit_code}" -eq 0 ]]; then
        RESULT[$scenario]="PASS"
    else
        RESULT[$scenario]="FAIL (exit ${exit_code})"
    fi
done

# ---- Summary ----
echo
echo "================================================================"
echo "Summary"
echo "================================================================"
overall_exit=0
for scenario in "${SCENARIOS[@]}"; do
    status="${RESULT[$scenario]}"
    printf "  %-18s  %s\n" "${scenario}" "${status}"
    if [[ "${status}" != "PASS" ]]; then
        overall_exit=1
    fi
done
echo
echo "Screenshots and generated scripts are under: ${OUT_DIR}"
exit "${overall_exit}"
