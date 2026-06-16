# ChatVis

We develop an iterative assistant we call ``ChatVis'' that can synthetically generate Python scripts for data analysis and visualization using a large language model (LLM). The assistant allows a user to specify the operations in natural language, attempting to generate a Python script for the desired operations, prompting the LLM to revise the script as needed until it executes correctly. The iterations include an error detection and correction mechanism that extracts error messages from the execution of the script and subsequently prompts LLM to correct the error. Our method demonstrates correct execution on five canonical visualization scenarios, comparing results with ground truth.

## Two implementations

This repository contains two parallel implementations:

- **`chatvis/` (active)** — a Python package that drives the full pipeline (prompt improvement → code generation → `pvpython` execution → bounded repair loop) against Argonne's Argo LLM endpoint. This is the recommended way to run ChatVis.
- **`notebooks/` (paper artifacts)** — five per-scenario Jupyter notebooks against plain OpenAI. Preserved verbatim for reproducibility of the published results; see the [Notebooks](#notebooks-paper-reproducibility) section.

See `AGENTS.md` for the authoritative developer guide (toolchain, prompt-source conventions, gotchas).

## Running the package

### Prerequisites

- Python 3.14 (managed by [`uv`](https://docs.astral.sh/uv/); `.python-version` pins it).
- `pvpython` on `$PATH`. If you don't have a system ParaView, the bundled `environment.yaml` provides one via conda:
    ```bash
    conda env create -f environment.yaml
    conda activate chatvis
    which pvpython
    ```
    The conda env exists solely to supply `pvpython`; the package itself still runs under uv-managed Python 3.14.
- An Argonne (`ANL`) username for Argo LLM authentication. The package targets Argo's OpenAI-compatible endpoint at `https://apps.inside.anl.gov/argoapi/v1`; the username is passed as the OpenAI `api_key`. **There is no `OPENAI_API_KEY` codepath in the package** — that is only used by the notebooks.

### Install

```bash
uv sync
```

### Single scenario

```bash
uv run python -m chatvis.main \
    --scenario stream-glyph \
    --data-filepath data/disk.ex2 \
    --screenshot-path /tmp/stream-glyph.png \
    --username <your-anl-id>
```

The generated ParaView script is written next to the screenshot (`/tmp/stream-glyph.py` in the example above). Exit codes: `0` clean run, `1` repair loop exhausted or no fenced python block returned, `2` pre-flight configuration error.

Useful flags: `--max-repair-attempts` (default 5), `--log-level debug`, `--log-file <path>`, `--pvpython <path>` (default: `shutil.which("pvpython")`).

### All scenarios

```bash
scripts/run-all-scenarios.sh <your-anl-id> [extra chatvis flags ...]
```

Writes `out/<scenario>.{png,py,log}` for each of the five scenarios, prints a summary table, and exits non-zero iff any scenario failed.

### Scenarios and datasets

| Scenario           | Dataset               |
| ------------------ | --------------------- |
| `stream-glyph`     | `data/disk.ex2`       |
| `points-surf-clip` | `data/can_points.ex2` |
| `ml-dvr`           | `data/ml-100.vtk`     |
| `ml-iso`           | `data/ml-100.vtk`     |
| `ml-slice-iso`     | `data/ml-100.vtk`     |

### Verifying a run

There is no automated screenshot diff. To verify a run:

1. Confirm the CLI exited `0`.
2. Visually compare the generated screenshot against `data/benchmark/<scenario>/<scenario>-screenshot.png` (when present — `ml-slice-iso` is currently a stub).
3. Inspect the generated `.py` against `data/benchmark/<scenario>/<scenario>.py` for major divergence.

`data/benchmark/` is untracked; it holds reference outputs and per-scenario `prompt.txt` files.

## Development

```bash
make create-dev          # pre-commit install + uv sync
uv run pytest tests -q   # run the unit test suite
pre-commit run --all-files
```

The test suite covers pure helpers in `chatvis.utils`, `chatvis.v1.script`, and `chatvis.llm`; it does not exercise the LLM, `pvpython`, or the orchestrator end-to-end.

The `prettier` pre-commit hook uses a system-installed `prettier`; install one (e.g. `npm i -g prettier`) before running pre-commit.

## Notebooks (paper reproducibility)

The five notebooks under `notebooks/` are preserved as paper artifacts. They predate the package, hard-code macOS author paths in several places, and use plain OpenAI (`gpt-4` / `gpt-4-turbo` / `gpt-4o`) rather than Argo. See `AGENTS.md` for the per-notebook differences and gotchas.

To run a notebook locally:

1. Install Jupyter and OpenAI:
    ```bash
    pip install jupyter openai
    ```
2. Edit the three hard-coded macOS paths per notebook (`extract_python_code` output filename, the `user_input` prompt text, and the `SaveScreenshot` path inside `code_to_save`) to point at local locations.
3. Paste your OpenAI key into the `OpenAI(api_key="")` call. Do not commit.
4. `jupyter notebook` and open the desired `<scenario>.ipynb`.
5. Run cells with `Shift + Enter` (or `Cell → Run All`).

Three of the five notebooks (`ml-dvr`, `ml-iso`, `ml-slice-iso`) also have a dead `import ollama` that will `ImportError` unless `pip install ollama`; it is unused.
