#!/usr/bin/env bash
# Run every ChatVis scenario against its expected dataset, for either the
# v1 or v2 pipeline.
#
# Command-line parsing is handled by optparse.bash (a getopts wrapper):
#   https://github.com/nk412/optparse
# Every option therefore has both a short and a long form, a description,
# and an auto-generated `--help` / `-?` usage screen.
#
# Usage:
#   scripts/run-all-scenarios.sh --username <anl-id> [options]
#   scripts/run-all-scenarios.sh -u <anl-id> -c v2 [options]
#
# Options (see --help for the authoritative list):
#   -u --username             ANL username (REQUIRED)
#   -c --chatvis-version      Pipeline to run: v1 or v2 (default: v1)
#   -m --model                LLM model (default: chatvis default, gpt4o)
#   -e --endpoint             LLM API endpoint URL (default: chatvis default)
#   -a --argo-shim                 Use Argonne Argo gateway quirks (no TLS verify + Host header): true|false (default: false)
#   -p --pvpython             Path to pvpython (default: first on PATH)
#   -l --log-level            debug|info|warning|error|critical (default: chatvis default)
#   -f --log-file             Enable chatvis file logging: true|false (default: false)
#   -r --max-repair-attempts  Repair-loop budget (default: chatvis default)
#   -k --top-k                v2 only: snippets to retrieve (default: chatvis default)
#   -i --faiss-index          v2 only: FAISS index path (default: chatvis default)
#   -d --metadata-lookup      v2 only: metadata-lookup pickle path (default: chatvis default)
#   -s --scenarios            Comma-separated subset of scenarios (default: all five)
#   -o --out-dir              Output directory (default: <repo>/out)
#
# The chatvis CLI is subcommand-based: global flags precede the `v1`/`v2`
# subcommand and per-pipeline flags follow it. This script maps the
# options above onto that structure automatically, so callers never have
# to remember the ordering or the v1-vs-v2 split.
#
# Examples:
#   scripts/run-all-scenarios.sh -u jdoe -a
#   scripts/run-all-scenarios.sh -u jdoe -a -c v2
#   scripts/run-all-scenarios.sh -u jdoe -a -r 10 -l debug
#   scripts/run-all-scenarios.sh -u jdoe -a -c v2 -k 8 -s stream-glyph,ml-iso
#   scripts/run-all-scenarios.sh --username jdoe --argo-shim --pvpython /opt/paraview/bin/pvpython
#
# Outputs (under --out-dir, default <repo>/out):
#   <scenario>.png   - generated screenshot
#   <scenario>.py    - generated ParaView script (sibling, written by chatvis)
#   <scenario>.log   - captured stdout+stderr of the chatvis invocation
#
# Behavior:
#   - Runs every selected scenario regardless of individual failures.
#   - Prints a pass/fail summary table at the end.
#   - Exits 0 only if every selected scenario exited 0.

set -u  # NB: not -e; we want to continue past failed scenarios.

# Resolve the repo root from the script's own location so the script
# can be invoked from any cwd.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

# ---- Argument parsing via optparse.bash ----
# optparse.bash reads several of its own locals without initialising
# them, which trips `set -u`; relax it only while the parser is being
# defined, built, and sourced, then restore strict mode.
# shellcheck source=scripts/optparse.bash
source "${SCRIPT_DIR}/optparse.bash"
set +u
optparse.define short=u long=username variable=USERNAME \
    desc="ANL username (required)"
optparse.define short=c long=chatvis-version variable=CHATVIS_VERSION \
    desc="Pipeline to run: v1 or v2" default="v1"
optparse.define short=m long=model variable=MODEL \
    desc="LLM model" default=""
optparse.define short=e long=endpoint variable=ENDPOINT \
    desc="LLM API endpoint URL" default=""
optparse.define short=a long=argo-shim variable=ARGO_SHIM \
    desc="Use Argonne Argo gateway quirks (no TLS verify + Host header)" \
    default="false" value="true"
optparse.define short=p long=pvpython variable=PVPYTHON \
    desc="Path to the pvpython executable" default=""
optparse.define short=l long=log-level variable=LOG_LEVEL \
    desc="Logging verbosity" default=""
optparse.define short=f long=log-file variable=LOG_FILE \
    desc="Enable chatvis file logging (true|false)" default="false" value="true"
optparse.define short=r long=max-repair-attempts variable=MAX_REPAIR \
    desc="Repair-loop budget" default=""
optparse.define short=k long=top-k variable=TOP_K \
    desc="v2 only: snippets to retrieve" default=""
optparse.define short=i long=faiss-index variable=FAISS_INDEX \
    desc="v2 only: FAISS index path" default=""
optparse.define short=d long=metadata-lookup variable=METADATA_LOOKUP \
    desc="v2 only: metadata-lookup pickle path" default=""
optparse.define short=s long=scenarios variable=SCENARIOS_OPT \
    desc="Comma-separated subset of scenarios" default=""
optparse.define short=o long=out-dir variable=OUT_DIR_OPT \
    desc="Output directory" default=""
optparse_build_file="$(optparse.build)"
# optparse only emits a default assignment when the default is a
# non-empty string (see optparse.bash: `if [ "$default" != "" ]`), so
# every option declared with default="" stays unset -- which trips
# `set -u` the moment the option is omitted. Seed them all here so an
# unset optional flag reads as the empty string rather than erroring.
USERNAME="" MODEL="" ENDPOINT="" PVPYTHON="" LOG_LEVEL="" \
    MAX_REPAIR="" TOP_K="" FAISS_INDEX="" METADATA_LOOKUP="" \
    SCENARIOS_OPT="" OUT_DIR_OPT=""
# shellcheck source=/dev/null
source "${optparse_build_file}"
set -u

# ---- Validate parsed options ----
if [[ -z "${USERNAME}" ]]; then
    echo "ERROR: --username/-u is required." >&2
    echo "Run '$0 --help' for usage." >&2
    exit 2
fi

if [[ "${CHATVIS_VERSION}" != "v1" && "${CHATVIS_VERSION}" != "v2" ]]; then
    echo "ERROR: --chatvis-version must be 'v1' or 'v2', got '${CHATVIS_VERSION}'." >&2
    exit 2
fi

DATA_DIR="${REPO_ROOT}/data"
OUT_DIR="${OUT_DIR_OPT:-${REPO_ROOT}/out}"
mkdir -p "${OUT_DIR}"

# Scenario -> dataset basename. Must mirror chatvis/main.py's
# _EXPECTED_DATA_BY_SCENARIO; if these drift, chatvis will warn at
# runtime but still proceed.
declare -A DATASET=(
    [ml-dvr]="ml-100.vtk"
    [ml-iso]="ml-100.vtk"
    [ml-slice-iso]="ml-100.vtk"
    [points-surf-clip]="can_points.ex2"
    [stream-glyph]="disk.ex2"
)

# Preserve insertion order via an explicit list (associative arrays
# have no defined iteration order in bash).
ALL_SCENARIOS=(
    ml-dvr
    ml-iso
    ml-slice-iso
    points-surf-clip
    stream-glyph
)

# Resolve the scenario list: a user-supplied comma-separated subset, or
# all five by default. Unknown names are rejected up front so a typo
# fails fast instead of producing a confusing per-scenario error.
SCENARIOS=()
if [[ -n "${SCENARIOS_OPT}" ]]; then
    IFS=',' read -r -a _requested <<< "${SCENARIOS_OPT}"
    for scenario in "${_requested[@]}"; do
        if [[ -z "${DATASET[$scenario]+x}" ]]; then
            echo "ERROR: unknown scenario '${scenario}'." >&2
            echo "Valid scenarios: ${ALL_SCENARIOS[*]}" >&2
            exit 2
        fi
        SCENARIOS+=("${scenario}")
    done
else
    SCENARIOS=("${ALL_SCENARIOS[@]}")
fi

# ---- Assemble the chatvis argument vectors ----
# Globals precede the subcommand; per-pipeline flags follow it. Only
# flags the caller actually set are forwarded, so chatvis applies its
# own defaults for everything left blank.
GLOBAL_ARGS=(--username "${USERNAME}")
[[ -n "${MODEL}" ]] && GLOBAL_ARGS+=(--model "${MODEL}")
[[ -n "${ENDPOINT}" ]] && GLOBAL_ARGS+=(--endpoint "${ENDPOINT}")
[[ -n "${PVPYTHON}" ]] && GLOBAL_ARGS+=(--pvpython "${PVPYTHON}")
[[ "${ARGO_SHIM}" != "false" ]] && GLOBAL_ARGS+=(--argo-shim)
[[ -n "${LOG_LEVEL}" ]] && GLOBAL_ARGS+=(--log-level "${LOG_LEVEL}")
[[ "${LOG_FILE}" != "false" ]] && GLOBAL_ARGS+=(--log-file)

# Per-pipeline (post-subcommand) flags common to v1 and v2.
PIPELINE_ARGS=()
[[ -n "${MAX_REPAIR}" ]] && PIPELINE_ARGS+=(--max-repair-attempts "${MAX_REPAIR}")

# v2-only RAG flags. Warn if the caller set them while running v1 so the
# silent no-op does not mislead.
if [[ "${CHATVIS_VERSION}" == "v2" ]]; then
    [[ -n "${TOP_K}" ]] && PIPELINE_ARGS+=(--top-k "${TOP_K}")
    [[ -n "${FAISS_INDEX}" ]] && PIPELINE_ARGS+=(--faiss-index "${FAISS_INDEX}")
    [[ -n "${METADATA_LOOKUP}" ]] && PIPELINE_ARGS+=(--metadata-lookup "${METADATA_LOOKUP}")
else
    if [[ -n "${TOP_K}" || -n "${FAISS_INDEX}" || -n "${METADATA_LOOKUP}" ]]; then
        echo "WARNING: --top-k/--faiss-index/--metadata-lookup are v2-only;" \
            "ignoring them for v1." >&2
    fi
fi

echo "ChatVis batch run"
echo "  version:    ${CHATVIS_VERSION}"
echo "  username:   ${USERNAME}"
echo "  out dir:    ${OUT_DIR}"
echo "  scenarios:  ${SCENARIOS[*]}"

declare -A RESULT  # scenario -> "PASS" | "FAIL (exit N)"

for scenario in "${SCENARIOS[@]}"; do
    data_file="${DATA_DIR}/${DATASET[$scenario]}"
    screenshot_path="${OUT_DIR}/${scenario}.png"
    log_path="${OUT_DIR}/${scenario}.log"

    echo
    echo "================================================================"
    echo "Scenario: ${scenario}  (${CHATVIS_VERSION})"
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
    #
    # The conditional expansion is needed because `set -u` makes
    # `"${arr[@]}"` an unbound-variable error when `arr` is empty under
    # older bash (pre-4.4).
    (
        cd "${REPO_ROOT}" && \
        uv run python -m chatvis.main \
            ${GLOBAL_ARGS[@]+"${GLOBAL_ARGS[@]}"} \
            "${CHATVIS_VERSION}" \
            --scenario "${scenario}" \
            --data-filepath "${data_file}" \
            --screenshot-path "${screenshot_path}" \
            ${PIPELINE_ARGS[@]+"${PIPELINE_ARGS[@]}"}
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
echo "Summary (${CHATVIS_VERSION})"
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
