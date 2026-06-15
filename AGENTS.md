# AGENTS.md

Research artifact for the ChatVis paper (LLM-driven ParaView script generation). **Two implementations coexist:** the original Jupyter notebooks under `notebooks/` (reference behavior preserved for the paper) and a Python package under `chatvis/` (the active migration target — partially wired, not yet end-to-end runnable). Notebook behavior is the source of truth; package code is the direction of travel.

## Layout

- `chatvis/` — installable package (Python 3.14). Real code now, no longer a stub. See "Package state" below.
    - `main.py`, `cli.py`, `llm.py`, `utils.py`, `logger.py`
    - `chatvis/documents/` — Pydantic-modelled prompt/code sources (`code_examples.py`, `code_generation.py`, `code_improvement.py`, `prompt_generation.py`, `prompt_generation_examples.py`).
    - `chatvis/v1/` — earlier refactor attempt. **Untracked**; superseded by `chatvis/documents/`. Do not edit or import unless asked.
- `notebooks/` — the five working scenario notebooks: `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`. ~90% near-duplicate scaffolds; duplication is **intentional for paper reproducibility** — do not refactor into a shared module without asking.
- `data/` — **flat layout** (was previously nested under `benchmark/` / `generated_data/`; those subdirs are gone). Contains `ml-100.vtk`, `disk.ex2`, `can_points.ex2`. Notebook paths still point at macOS author paths, not `data/` — edit them when running locally.
- `dist/`, `chatvis.egg-info/` — build artifacts; safe to ignore / not commit.
- `session-ses_*.md` at repo root — agent session transcripts; informational, not code.

## Toolchain (Python 3.14, uv-managed)

- `pyproject.toml` requires `python>=3.14`; `.python-version` pins `3.14`. `.venv/` at repo root is the working env.
- **Version mismatch to know:** `.pre-commit-config.yaml` sets `default_language_version: python: python3.13`. Pre-commit hooks run under 3.13 even though the project targets 3.14. Do not "fix" without confirming.
- `Makefile` targets:
    - `make create-dev` → `pre-commit install && pre-commit autoupdate && rm -rf env && uv sync`
    - `make build` → `git tag | … | tail -n 1 | xargs -I % uv version %`, then `uv build`, then `uv pip install dist/*.tar.gz`. **There are currently no git tags**, so `make build` will pass an empty version to `uv version` and fail. Create a tag first or skip `make build`.
- Dependencies: `openai>=2.41`, `pandas>=3.0.3`, `pydantic>=2.13.4`. Dev: `jupyter>=1.1.1`, `pytest>=9.0.3`.
- **`pytest` is a declared dev dep, but there is no `tests/` directory and no test files anywhere.** Don't assume a test suite exists.
- **No CI workflows, no `[tool.ruff]` config** (ruff runs on defaults via pre-commit).
- Lint/format/security pipeline lives in pre-commit only. Order: `isort` → `ruff-format` → `ruff-check` → `bandit`. Run via `pre-commit run --all-files`. There is no separate `make lint` target.
- Notebooks are committed **with output cells** (large base64 PNGs). Re-running rewrites execution counts and outputs — inspect `git diff` carefully and ask before committing notebook output churn.

## Package state (`chatvis/`, active migration — partially working)

The package targets **Argonne's Argo API**, an OpenAI-compatible endpoint (`DEFAULT_ENDPOINT = "https://apps.inside.anl.gov/argoapi/v1"` in `chatvis/cli.py`). Authentication is by ANL username passed as `api_key` to the OpenAI `Client` (see comment in `chatvis/llm.py:21`). It is **not** plain OpenAI; do not "fix" the empty-looking key handling by adding `OPENAI_API_KEY` loading.

- Entry point: `python -m chatvis.main --scenario <s> --data-filepath <p> --screenshot-path <p> --username <anl-user>`. `--model` is currently restricted to `["gpt4o"]` (see `MODELS` in `cli.py`).
- Current flow in `main.py:main` does: parse CLI → configure logging → validate that data file matches scenario (`check_data`) → handshake to Argo (`connect_to_argo`) → run **prompt generation only** (`generate_improved_prompt`). Code generation and the code-improvement loop are implemented in `chatvis/llm.py` (`code_generation`, `code_improvement`) but **not yet called from `main`**.
- **Known bugs / unfinished spots to be aware of (do not assume these are "yours to fix" — ask first):**
    - `chatvis/main.py:113` calls `cli_parser()`, which does not exist and is not imported. `chatvis/cli.py` exposes a `CLI` class with a `parser()` method instead. **The CLI does not run as-is**; this is the next thing to wire up.
    - `chatvis/documents/code_improvement.py:29` mixes templating styles: the surrounding template is `string.Template` (uses `${...}`), but `{prompt}` is written with curly braces. `Template.substitute` will leave it verbatim. Likely intended to be `${prompt}`.
    - `chatvis/documents/prompt_generation_examples.py` for `ml-slice-iso` uses `<input_file>` / `<output_file>` (lines 84, 90); the rest of the codebase uses `<input_path>` / `<output_path>`. Likely a typo.
    - `PROMPT_GENERATION_EXAMPLES["points-surf-clip"].generated_prompt` is `""`, and `chatvis/main.py:94` raises `ValueError` when that field is empty. The `points-surf-clip` scenario therefore fails fast under the current code path until the example is filled in.
- Conventions worth following when extending:
    - All sources are Pydantic `BaseModel`s in `chatvis/documents/`.
    - Code snippets in `CODE_EXAMPLES` use **angle-bracket sentinels** (`<input_path>`, `<output_path>`), not `str.format` fields. They are intended to be string-substituted by the LLM, not by Python.
    - Prompt user templates use `string.Template` with `$name` / `${name}` (see `chatvis/documents/prompt_generation.py`).
    - Logging: every submodule should use `logging.getLogger(__name__)`; `chatvis/logger.py` configures the `chatvis` root logger and disables propagation.

## Notebook gotchas (all five files, still present)

- **Hard-coded macOS author paths** are baked into every notebook in three places: `extract_python_code` output filename, the `user_input` prompt text (input dataset path), and the `SaveScreenshot` path inside `code_to_save`. All point at `/Users/tanwimallick/Documents/Paraview/generated_code/`. Edit **all three** per notebook to run elsewhere.
- **macOS-only `pvpython` path** prepended to `PATH`: `"/Applications/ParaView-5.12.0.app/Contents/bin:$PATH"`. No-op on Linux; ensure `pvpython` (ParaView 5.12) is otherwise on `PATH`.
- **`OpenAI(api_key="")`** in the notebooks — no env-var loading. Paste key directly; do not commit. (The package code path uses Argo and `--username`, not this.)
- **Dead `import ollama`** in `ml-dvr.ipynb`, `ml-iso.ipynb`, `ml-slice-iso.ipynb` (never called). Notebook will `ImportError` without `pip install ollama` even though removing the import would also work. `ollama` is NOT in `pyproject.toml` deps.
- **`extract_python_code` early-return bug in the notebooks**: `return filename` sits inside the `for` loop, so only the first `python` block from the LLM response is ever saved. Present in all five. The package version in `chatvis/utils.py` has a different, correct implementation that returns `list[str]` — do not assume parity.

## Per-notebook behavioral differences (verify before editing — easy to get wrong)

- `stream-glyph.ipynb` — **active** `while errors:` correction loop. `gpt-4` for both generation and repair.
- `points-surf-clip.ipynb` — **active** `while errors:` correction loop. `gpt-4-turbo` for generation, `gpt-4` inside the loop.
- `ml-dvr.ipynb` — `while errors:` block is **commented out**; runs exactly one generation attempt. `gpt-4o` for prompt generation, `gpt-4-turbo` for code generation.
- `ml-iso.ipynb` — no correction loop, but the `subprocess.run` / `extract_error_messages` block is **literally duplicated** (two adjacent cells run the generated script twice with no loop). Likely a copy-paste bug; preserve as-is unless asked. `gpt-4o` then `gpt-4-turbo`.
- `ml-slice-iso.ipynb` — no correction loop. Models are swapped vs the others: `gpt-4-turbo` for prompt generation, `gpt-4o` for code generation.

## Datasets

- `data/disk.ex2` — used by `stream-glyph`.
- `data/can_points.ex2` — used by `points-surf-clip`.
- `data/ml-100.vtk` — used by `ml-dvr`, `ml-iso`, `ml-slice-iso`.
- `check_data` in `chatvis/main.py:36` is the authoritative scenario↔file mapping. Notebooks still reference the old macOS path, not `data/`.

## Working on this repo

- "Verification" of a scenario = run the notebook (or, eventually, the package CLI) end-to-end against `pvpython` (ParaView 5.12) and visually compare the generated screenshot to the reference. There is no automated test step.
- When changing a helper that exists in multiple notebooks (`extract_python_code`, `extract_error_messages`, the `code_to_*` snippets), apply the same edit to every notebook that has it. Do not consolidate into a shared module without explicit request.
- When porting more notebook behavior into `chatvis/`, follow the existing pattern: Pydantic models under `chatvis/documents/`, logic in `chatvis/llm.py`, wired through `chatvis/main.py`.
- Avoid `jq` / raw-JSON edits to `.ipynb` files. Use Jupyter or `nbconvert` and understand the cell schema first.
- `README.md` covers only the legacy "install jupyter, paste key, run cells" notebook flow. It does not mention the package, `uv`, pre-commit, Argo, the hard-coded paths, or any of the above gotchas. Treat this `AGENTS.md` as authoritative when they conflict.
