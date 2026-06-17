# ChatVis

ChatVis is an iterative LLM-driven assistant that turns a natural-language
description of a scientific visualization into a working ParaView (`pvpython`)
script. It improves the user's prompt, asks the LLM to synthesise a script,
executes the script, detects failures (Python tracebacks and silent
VTK/ParaView pipeline failures), and re-prompts the LLM in a bounded repair
loop until the script either runs cleanly or the repair budget is exhausted.

DOI: `<DOI placeholder>`

## How it works

The `v1` pipeline (the only one wired today) runs four stages plus a bounded
repair loop:

1. **Prompt improvement** — `chatvis.llm.improve_prompt` rewrites the chosen
   scenario's stock description into an LLM-improved prompt, using a
   few-shot pair from a different scenario family so the LLM is never shown
   its own answer.
2. **Code generation** — `chatvis.llm.generate_code` asks the LLM for a
   ParaView script implementing the improved prompt.
3. **Extract and persist** — `chatvis.v1.script.first_python_block` pulls the
   first fenced Python block from the LLM response and writes it next to the
   requested screenshot path.
4. **Execute under `pvpython`** — `chatvis.v1.pvpython.run_pvpython` runs the
   script. If a Python traceback (or one of a small allow-list of silent
   VTK/ParaView failure messages) is detected, `chatvis.llm.improve_code` is
   called in a loop bounded by `--max-repair-attempts`; on each iteration the
   LLM sees the on-disk script, the captured errors, and the previous run's
   stdout.

## Installation

### Prerequisites

- **Python 3.14**, managed by [`uv`](https://docs.astral.sh/uv/). The
  project pins this via `.python-version`.
- **`pvpython` on `PATH`.** If you don't have a system ParaView, the bundled
  conda env exists solely to put one on `PATH`:
    ```bash
    conda env create -f environment.yaml
    conda activate chatvis
    which pvpython
    ```
    The conda env supplies `pvpython` only; ChatVis itself still runs under
    uv-managed Python 3.14.
- **An Argonne (ANL) username.** ChatVis targets Argonne's Argo LLM service
  (an OpenAI-compatible endpoint at `https://apps.inside.anl.gov/argoapi/v1`).
  The username is passed as `--username` and used as the OpenAI `api_key`
  by the underlying client. There is no `OPENAI_API_KEY` codepath.

### Install

```bash
uv sync
```

This creates `.venv/`, installs the runtime dependencies (`openai`, `numpy`),
and registers the `chatvis` console script declared in `pyproject.toml`.

## Development environment

```bash
make create-dev          # pre-commit install + autoupdate + uv sync
uv run pytest tests -q   # run the unit test suite
pre-commit run --all-files
```

The test suite covers pure helpers in `chatvis.utils`, `chatvis.v1.script`,
and `chatvis.llm`. It does not exercise the LLM client, `pvpython`, or the
end-to-end orchestrator, both of which need either a live backend or a
non-trivial stub.

The `prettier` pre-commit hook shells out to a system-installed `prettier`
binary; install one (for example, `npm i -g prettier`) before running
pre-commit, or that hook will fail.

## Running ChatVis

The CLI is subcommand-based. **Global flags must precede the subcommand;
subcommand-specific flags must follow it.** Today only the `v1` subcommand is
wired; `v2` is reserved for a future RAG-based agent and currently exits
non-zero with a placeholder error.

### Single scenario

```bash
uv run python -m chatvis.main \
    --username <your-anl-id> \
    --argo \
    v1 \
    --scenario stream-glyph \
    --data-filepath data/disk.ex2 \
    --screenshot-path /tmp/stream-glyph.png
```

Equivalently, after `uv sync`:

```bash
uv run chatvis \
    --username <your-anl-id> \
    --argo \
    v1 \
    --scenario stream-glyph \
    --data-filepath data/disk.ex2 \
    --screenshot-path /tmp/stream-glyph.png
```

`--argo` configures the client for Argonne's internal Argo gateway
(disables TLS certificate verification and sends a
`Host: apps.inside.anl.gov` header). It is **off by default**; drop it
when targeting a standards-compliant OpenAI-compatible endpoint.

### All scenarios

```bash
scripts/run-all-scenarios.sh --username <your-anl-id> [options]
```

The script runs each of the five scenarios against its expected dataset,
continues past individual failures, and prints a pass/fail summary. Every
option has a short and long form; see `--help` for the full list. Pass
`--argo`/`-a` to enable the internal Argo gateway quirks. Examples:

```bash
scripts/run-all-scenarios.sh -u jdoe -a
scripts/run-all-scenarios.sh -u jdoe -a -r 10
scripts/run-all-scenarios.sh -u jdoe -a -l debug -r 10
```

### Scenarios and datasets

| Scenario           | Dataset               |
| ------------------ | --------------------- |
| `stream-glyph`     | `data/disk.ex2`       |
| `points-surf-clip` | `data/can_points.ex2` |
| `ml-dvr`           | `data/ml-100.vtk`     |
| `ml-iso`           | `data/ml-100.vtk`     |
| `ml-slice-iso`     | `data/ml-100.vtk`     |

Mismatches between `--scenario` and `--data-filepath` are warned about but
not rejected — `pvpython` and the LLM both accept whatever path you supply.

### CLI options

Global flags (apply to every subcommand):

| Flag              | Default                                  | Notes                                                                                              |
| ----------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `--username`      | _required_                               | ANL username; used as the Argo API key.                                                            |
| `--model`         | `gpt4o`                                  | Only `gpt4o` is currently accepted.                                                                |
| `--endpoint`      | `https://apps.inside.anl.gov/argoapi/v1` | Argo OpenAI-compatible endpoint.                                                                   |
| `--argo`          | _off_                                    | Disable TLS verification + send `Host: apps.inside.anl.gov`; needed for the internal Argo gateway. |
| `--pvpython`      | `shutil.which("pvpython")`               | Override if `pvpython` is not on `PATH`.                                                           |
| `--log-file`      | _off_                                    | Also write logs to `<cwd>/chatvis_<unix-seconds>.log`.                                             |
| `--log-level`     | `info`                                   | One of `debug`, `info`, `warning`, `error`, `critical`.                                            |
| `-V`, `--version` | —                                        | Print the installed version and exit.                                                              |

`v1` subcommand flags:

| Flag                    | Default    | Notes                                                                               |
| ----------------------- | ---------- | ----------------------------------------------------------------------------------- |
| `--scenario`            | `ml-dvr`   | One of `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`.      |
| `--data-filepath`       | _required_ | Absolute or relative path to the dataset to visualise.                              |
| `--screenshot-path`     | _required_ | Where the generated screenshot will be written; the script is written alongside it. |
| `--max-repair-attempts` | `5`        | Maximum LLM repair iterations after the initial generation attempt.                 |

## Outputs

### Single-scenario run

- **Generated script** — a Python file written next to `--screenshot-path`
  with the suffix replaced by `.py`. For example,
  `--screenshot-path /tmp/stream-glyph.png` produces
  `/tmp/stream-glyph.py`.
- **Screenshot** — the PNG written by the generated script at exactly
  `--screenshot-path`. (If the script never reaches the `SaveScreenshot`
  call, no PNG will be produced even when ChatVis exits `0`; this is rare
  but possible when a silent VTK failure leaves earlier stages partly
  populated.)
- **Log file** — when `--log-file` is given, a UTC-timestamped log at
  `<cwd>/chatvis_<unix-seconds>.log`.

### Batch run (`scripts/run-all-scenarios.sh`)

For each scenario, the script writes:

- `out/<scenario>.png` — generated screenshot.
- `out/<scenario>.py` — generated ParaView script (written by ChatVis as
  the sibling of the screenshot).
- `out/<scenario>.log` — captured stdout + stderr of the `chatvis`
  invocation.

A pass/fail summary table is printed at the end. The script's overall exit
code is `0` only if every scenario exited `0`.

### Exit codes

| Code | Meaning                                                                                   |
| ---- | ----------------------------------------------------------------------------------------- |
| `0`  | Script executed cleanly (no extracted tracebacks).                                        |
| `1`  | Repair loop exhausted, or the LLM response contained no fenced Python block.              |
| `2`  | Pre-flight configuration error (missing data file, missing or non-executable `pvpython`). |
| `3`  | Selected subcommand is not implemented (e.g. `v2`).                                       |

### Verifying a run

There is no automated screenshot diff. To verify a run:

1. Confirm the CLI exited `0`.
2. Visually compare the generated screenshot against the reference under
   `data/benchmark/<scenario>/<scenario>-screenshot.png` (when present).
3. Inspect the generated `.py` against
   `data/benchmark/<scenario>/<scenario>.py` for major divergence.

`data/benchmark/` is untracked; it holds per-scenario reference outputs and
prompt files used for manual verification.
