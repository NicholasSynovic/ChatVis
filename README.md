# ChatVis

ChatVis is an iterative LLM-driven assistant that turns a natural-language
description of a scientific visualization into a working ParaView (`pvpython`)
script. It improves the user's prompt (or retrieves relevant code examples),
asks the LLM to synthesise a script, executes the script, detects failures
(Python tracebacks and silent VTK/ParaView pipeline failures), and re-prompts
the LLM in a bounded repair loop until the script either runs cleanly or the
repair budget is exhausted.

ChatVis ships two pipelines, both wired into the CLI as subcommands:

- **`v1`** — the original few-shot pipeline. It rewrites the scenario prompt
  with an LLM-improved version before generating code.
- **`v2`** — a retrieval-augmented (RAG) pipeline. It retrieves relevant
  ParaView code snippets from a FAISS index and injects them into the
  code-generation prompt instead of running a prompt-improvement stage.

DOIs:

- v1: <https://doi.org/10.1109/SCW63240.2024.00014>
- v2: <https://doi.org/10.1109/LDAV68558.2025.00007>

## How it works

### v1 pipeline

The `v1` pipeline runs four stages plus a bounded repair loop:

1. **Prompt improvement** — `chatvis.llm.improve_prompt_v1` rewrites the
   chosen scenario's stock description into an LLM-improved prompt, using a
   few-shot pair from a different scenario family so the LLM is never shown
   its own answer.
2. **Code generation** — `chatvis.llm.generate_code_v1` asks the LLM for a
   ParaView script implementing the improved prompt.
3. **Extract and persist** — `chatvis.script.first_python_block` pulls the
   first fenced Python block from the LLM response and
   `chatvis.script.write_script` writes it next to the requested screenshot
   path.
4. **Execute under `pvpython`** — `chatvis.pvpython.run_pvpython` runs the
   script. If a Python traceback (or one of a small allow-list of silent
   VTK/ParaView failure messages) is detected, `chatvis.llm.improve_code_v1`
   is called in a loop bounded by `--max-repair-attempts`; on each iteration
   the LLM sees the on-disk script, the captured errors, and the previous
   run's stdout.

### v2 pipeline

The `v2` pipeline replaces prompt improvement with retrieval. It runs three
stages plus the same bounded repair loop:

1. **Retrieval** — the scenario description is used to query a FAISS index of
   ParaView code snippets (built on demand via
   `chatvis.v2.documents.code.CodeEmbeddings`). The first build downloads the
   sentence-transformers embedding model and embeds every bundled snippet, so
   it can be slow on a cold cache.
2. **Code generation** — `chatvis.llm.generate_code_v2` asks the LLM for a
   ParaView script, injecting the retrieved snippets into the user prompt.
3. **Execute under `pvpython`** — `chatvis.pvpython.run_pvpython` runs the
   script, and `chatvis.llm.improve_code_v2` drives the bounded repair loop
   when a failure is detected.

## Downloading the project

Clone the repository and change into it:

```bash
git clone git@github.com:NicholasSynovic/ChatVis.git
cd ChatVis
```

Or over HTTPS:

```bash
git clone https://github.com/NicholasSynovic/ChatVis.git
cd ChatVis
```

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

This creates `.venv/`, installs the runtime dependencies, and registers the
`chatvis` console script declared in `pyproject.toml`. The runtime
dependencies are `openai`, `numpy`, `faiss-cpu`, `pandas`, `progress`, and
`sentence-transformers`. Only `openai` is needed by the `v1` path; the
remaining packages power the `v2` RAG pipeline.

## Development environment

```bash
make create-dev          # pre-commit install + autoupdate + uv sync
uv run pytest tests -q   # run the unit test suite
pre-commit run --all-files
```

The test suite (45 tests) covers pure helpers in `chatvis.utils`,
`chatvis.script`, and `chatvis.llm`, the `OpenAIModel` Argo construction and
temperature-retry paths, the `v2` LLM helpers (`generate_code_v2`,
`improve_code_v2`), and the `run_v2_pipeline` wiring. It does not exercise the
live LLM request path, `pvpython`, or `run_v1_pipeline` end to end, since
those need either a live backend or a non-trivial stub.

The `prettier` pre-commit hook shells out to a system-installed `prettier`
binary; install one (for example, `npm i -g prettier`) before running
pre-commit, or that hook will fail. Note that pre-commit pins Python 3.13 for
its hooks even though the project targets 3.14.

## Running ChatVis

The CLI is subcommand-based. **Global flags must precede the subcommand;
subcommand-specific flags must follow it.** Both the `v1` and `v2`
subcommands are wired.

### Running v1

```bash
uv run python -m chatvis.main \
    --username <your-anl-id> \
    --argo-shim \
    v1 \
    --scenario stream-glyph \
    --data-filepath data/disk.ex2 \
    --screenshot-path /tmp/stream-glyph.png
```

Equivalently, after `uv sync`:

```bash
uv run chatvis \
    --username <your-anl-id> \
    --argo-shim \
    v1 \
    --scenario stream-glyph \
    --data-filepath data/disk.ex2 \
    --screenshot-path /tmp/stream-glyph.png
```

`--argo-shim` configures the client for Argonne's internal Argo gateway
(disables TLS certificate verification and sends a
`Host: apps.inside.anl.gov` header). It is **off by default**; drop it
when targeting a standards-compliant OpenAI-compatible endpoint.

### Running v2

The `v2` invocation mirrors `v1` but selects the `v2` subcommand and accepts
optional RAG flags:

```bash
uv run python -m chatvis.main \
    --username <your-anl-id> \
    --argo-shim \
    v2 \
    --scenario stream-glyph \
    --data-filepath data/disk.ex2 \
    --screenshot-path /tmp/stream-glyph.png \
    --top-k 5
```

The FAISS index and metadata lookup are loaded from `--faiss-index` /
`--metadata-lookup` when present, and **built on demand** when missing. The
first build downloads the sentence-transformers embedding model and embeds
every bundled snippet, so the first `v2` run on a cold cache can take a while.

### All scenarios

```bash
scripts/run-all-scenarios.sh --username <your-anl-id> [options]
```

The script runs each of the five scenarios against its expected dataset,
continues past individual failures, and prints a pass/fail summary. Every
option has a short and long form; see `--help` for the full list. Pass
`--argo-shim`/`-a` to enable the internal Argo gateway quirks, and
`--chatvis-version`/`-c v2` to run the `v2` pipeline instead of `v1`.
Examples:

```bash
scripts/run-all-scenarios.sh -u jdoe -a
scripts/run-all-scenarios.sh -u jdoe -a -r 10
scripts/run-all-scenarios.sh -u jdoe -a -l debug -r 10
scripts/run-all-scenarios.sh -u jdoe -a -c v2 -k 8 -s stream-glyph,ml-iso
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

| Flag              | Default                                  | Notes                                                                                                                                               |
| ----------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--username`      | _required_                               | ANL username; used as the Argo API key.                                                                                                             |
| `--model`         | `gpt41`                                  | One of 15 models (see `MODELS` in `chatvis/cli.py`). Some GPT-5 / o-series models only accept `temperature=1`, which ChatVis handles automatically. |
| `--endpoint`      | `https://apps.inside.anl.gov/argoapi/v1` | Argo OpenAI-compatible endpoint.                                                                                                                    |
| `--argo-shim`     | _off_                                    | Disable TLS verification + send `Host: apps.inside.anl.gov`; needed for the internal Argo gateway.                                                  |
| `--pvpython`      | `shutil.which("pvpython")`               | Override if `pvpython` is not on `PATH`.                                                                                                            |
| `--log-file`      | _off_                                    | Also write logs to `<cwd>/chatvis_<unix-seconds>.log`.                                                                                              |
| `--log-level`     | `info`                                   | One of `debug`, `info`, `warning`, `error`, `critical`.                                                                                             |
| `-V`, `--version` | —                                        | Print the installed version and exit.                                                                                                               |

`v1` subcommand flags:

| Flag                    | Default    | Notes                                                                               |
| ----------------------- | ---------- | ----------------------------------------------------------------------------------- |
| `--scenario`            | `ml-dvr`   | One of `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`.      |
| `--data-filepath`       | _required_ | Absolute or relative path to the dataset to visualise.                              |
| `--screenshot-path`     | _required_ | Where the generated screenshot will be written; the script is written alongside it. |
| `--max-repair-attempts` | `5`        | Maximum LLM repair iterations after the initial generation attempt.                 |

`v2` subcommand flags (the scenario/data/repair flags above plus the RAG
flags below):

| Flag                    | Default                  | Notes                                                                               |
| ----------------------- | ------------------------ | ----------------------------------------------------------------------------------- |
| `--scenario`            | `ml-dvr`                 | One of `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`.      |
| `--data-filepath`       | _required_               | Absolute or relative path to the dataset to visualise.                              |
| `--screenshot-path`     | _required_               | Where the generated screenshot will be written; the script is written alongside it. |
| `--max-repair-attempts` | `5`                      | Maximum LLM repair iterations after the initial generation attempt.                 |
| `--faiss-index`         | `faiss.index`            | Path to the FAISS index of ParaView code snippets; built on demand if missing.      |
| `--metadata-lookup`     | `metadata_lookup.pickle` | Path to the pickled snippet metadata lookup paired with the FAISS index.            |
| `--top-k`               | `5`                      | Number of code snippets to retrieve from the FAISS index per query.                 |

## Running the benchmark

`data/benchmark/` is **tracked** and holds per-scenario reference outputs used
for manual verification. Each `data/benchmark/<scenario>/` directory contains:

- `<scenario>.py` — the reference ParaView script.
- `<scenario>-screenshot.png` — the reference screenshot.
- `prompt.txt` — the prompt used to produce the reference.
- the dataset the scenario consumes.

To benchmark a run, generate outputs and compare them against the references.
For a single scenario, run the relevant `v1`/`v2` command above and compare
the generated `.py` and `.png` against the matching files in
`data/benchmark/<scenario>/`. For all five scenarios at once, use the batch
script (which writes its outputs under `out/`):

```bash
scripts/run-all-scenarios.sh --username <your-anl-id> --argo-shim
```

There is no automated screenshot diff. To verify a run:

1. Confirm the CLI exited `0`.
2. Visually compare the generated screenshot against the reference under
   `data/benchmark/<scenario>/<scenario>-screenshot.png`.
3. Inspect the generated `.py` against
   `data/benchmark/<scenario>/<scenario>.py` for major divergence.

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

For each scenario, the script writes (under `--out-dir`, default `out/`):

- `out/<scenario>.png` — generated screenshot.
- `out/<scenario>.py` — generated ParaView script (written by ChatVis as
  the sibling of the screenshot).
- `out/<scenario>.log` — captured stdout + stderr of the `chatvis`
  invocation.

A pass/fail summary table is printed at the end. The script's overall exit
code is `0` only if every scenario exited `0`.

### Exit codes

| Code | Meaning                                                                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------------------ |
| `0`  | Script executed cleanly (no extracted tracebacks).                                                                       |
| `1`  | Repair loop exhausted, or the LLM response contained no fenced Python block.                                             |
| `2`  | Pre-flight configuration error (missing data file, missing/non-executable `pvpython`, or a missing `v2` RAG dependency). |

## Repository layout

A brief map of the most relevant paths. See `AGENTS.md` for the authoritative,
in-depth description of the codebase.

- `chatvis/` — the installable package.
    - `cli.py`, `main.py`, `llm.py` — argument parsing, orchestration, and the
      LLM client / pipeline-stage helpers.
    - `script.py`, `pvpython.py`, `utils.py` — shared helpers for script
      extraction/persistence, `pvpython` execution, and error parsing.
    - `v1/` — `v1` prompts and few-shot documents.
    - `v2/` — `v2` RAG corpus and embeddings (`documents/code.py`,
      `prompts/`).
- `notebooks/` — the five scenario notebooks, kept as paper-reproducibility
  artifacts.
- `data/` — the datasets plus the tracked `data/benchmark/` reference set.
- `scripts/run-all-scenarios.sh` — the batch driver.
- `environment.yaml` — conda env whose only job is to supply `pvpython`.

## Citation

If you use ChatVis, please cite the relevant work:

- v1: <https://doi.org/10.1109/SCW63240.2024.00014>
- v2: <https://doi.org/10.1109/LDAV68558.2025.00007>

## License

TBD. A license has not yet been specified for this project.

## Acknowledgements

This work builds on and is indebted to the following prior efforts:

- [SciVisAgentSkills (`paraview-viz`)](https://github.com/KuangshiAi/SciVisAgentSkills/tree/main/paraview-viz)
  — Claude Code agent skills for ParaView scientific visualization (volume
  rendering, isosurfaces, streamlines, and more).
- [HPC Skills (`hpc-paraview`)](https://github.com/SciMate-AI/HPC-Skills/tree/main/skills/hpc-paraview)
  — an HPC-oriented ParaView agent skill from SciMate-AI.
- [ParaView Skills](https://github.com/TouKaienn/Paraview-Skills) — a Claude
  Code skill for creating and manipulating 3D ParaView visualizations.
- [nl2scivis](https://github.com/goodbadwolf/nl2scivis) — the NL2SciVis
  benchmark for evaluating natural-language-to-ParaView-script generation.
- [ChatVis (tanwimallick)](https://github.com/tanwimallick/ChatVis) — the
  original ChatVis notebooks that this artifact reimplements and preserves.
- [ChatVis (tpeterka)](https://github.com/tpeterka/ChatVis) — the ChatVis
  scientific visualization agent and benchmark suite.
