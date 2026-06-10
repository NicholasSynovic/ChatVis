# AGENTS.md

Research artifact for the ChatVis paper (LLM-driven ParaView script generation). **The repo is mid-migration**: the original five Jupyter notebooks under `notebooks/` are the working reference implementation; a `chatvis/` Python package is being built to replace them but is **not yet runnable**. Treat the notebooks as the source of truth for behavior, and the package as scaffolding under active construction.

## Layout

- `chatvis/` — package under construction (Python 3.14, see below). Currently:
  - `main.py` — argparse CLI scaffold; every scenario `case` branch is `pass`. **CLI is a no-op.**
  - `llm.py` — entirely commented out.
  - `utils.py`, `code_examples.py`, `prompts.py` — partial data extracted from the notebooks into Pydantic models.
  - No notebook imports from `chatvis/` yet.
- `notebooks/` — the five working scenario notebooks: `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`. Near-duplicate scaffolds (~90% shared code); duplication is intentional for paper reproducibility — do not refactor into a shared module without asking.
- `data/benchmark/<scenario>/` — reference `prompt.txt`, hand-written `*.py`, expected `*-screenshot.png`, and for two scenarios the input dataset.
- `data/generated_data/<scenario>/` — committed sample of one prior generated script + screenshot. **Naming inconsistency**: `data/generated_data/stream_glyph/` (underscore) vs every other scenario dir (hyphen). Mirrors the same inconsistency in `data/benchmark/` (everything hyphen there). Do not "normalize" without asking.

## Toolchain (Python 3.14, uv-managed)

- `pyproject.toml` requires `python>=3.14`; `.python-version` pins `3.14`. `.venv/` at repo root is the working env.
- **Version mismatch to know**: `.pre-commit-config.yaml` sets `default_language_version: python: python3.13`. Pre-commit hooks run under 3.13 even though the project targets 3.14. Don't "fix" this without confirming.
- `Makefile` targets:
  - `make create-dev` → `pre-commit install && pre-commit autoupdate && rm -rf env && uv sync`
  - `make build` → tags the version from the latest git tag, `uv build`, `uv pip install dist/*.tar.gz`. No PyPI publish step.
- Dependencies: `openai>=2.41`, `pandas>=3.0.3`, `pydantic>=2.13.4`. Dev: `jupyter>=1.1.1`. No `ollama` in `pyproject.toml` even though three notebooks still `import ollama` (dead import — see below).
- **No tests, no CI workflows, no `[tool.ruff]` config** (ruff runs on defaults via pre-commit).
- Lint/format pipeline (pre-commit only, no separate lint command): `isort` → `ruff-format` → `ruff-check` → `bandit`. Run via `pre-commit run --all-files`.
- Notebooks are committed **with output cells** (large base64 PNGs). Re-running a notebook rewrites execution counts and outputs — inspect `git diff` carefully and ask the user before committing notebook output churn.

## Notebook gotchas (still present, all five files)

- **Hard-coded macOS author paths** are baked into every notebook in three places: `extract_python_code` output filename, the `user_input` prompt text (input dataset path), and the `SaveScreenshot` path inside `code_to_save`. All point at `/Users/tanwimallick/Documents/Paraview/generated_code/`. Edit **all three** per notebook to run elsewhere.
- **macOS-only `pvpython` path** prepended to `PATH`: `"/Applications/ParaView-5.12.0.app/Contents/bin:$PATH"`. No-op on Linux; ensure `pvpython` (ParaView 5.12) is otherwise on `PATH`.
- **`OpenAI(api_key="")`** — no env-var loading. Paste key directly; do not commit.
- **Dead `import ollama`** in `ml-dvr.ipynb`, `ml-iso.ipynb`, `ml-slice-iso.ipynb` (never called). Notebook will `ImportError` without `pip install ollama` even though removing the import would also work. `ollama` is NOT in `pyproject.toml` dependencies.
- **`extract_python_code` early-return bug**: `return filename` sits **inside** the `for` loop, so only the first ```python``` block from the LLM response is ever saved. Present in all five notebooks. The `chatvis/utils.py` version has a *different* bug (appends to the same `code_blocks` list it is iterating — produces duplicate entries); do not assume the package version is the fixed one.

## Per-notebook behavioral differences (verify before editing — easy to get wrong)

- `stream-glyph.ipynb` — **active** `while errors:` correction loop. `gpt-4` for both generation and repair.
- `points-surf-clip.ipynb` — **active** `while errors:` correction loop. `gpt-4-turbo` for generation, `gpt-4` inside the loop.
- `ml-dvr.ipynb` — `while errors:` block is **commented out**; runs exactly one generation attempt. `gpt-4o` for prompt generation, `gpt-4-turbo` for code generation.
- `ml-iso.ipynb` — no correction loop, but the `subprocess.run` / `extract_error_messages` block is **literally duplicated** (two adjacent cells run the generated script twice with no loop). Likely a copy-paste bug; preserve as-is unless asked to fix. `gpt-4o` then `gpt-4-turbo`.
- `ml-slice-iso.ipynb` — no correction loop. Models are swapped vs the others: `gpt-4-turbo` for prompt generation, `gpt-4o` for code generation.

## Datasets

- `data/benchmark/stream-glyph/disk.ex2` — shipped (used by `stream-glyph`).
- `data/benchmark/points-surf-clip/can_points.ex2` — shipped (used by `points-surf-clip`).
- `ml-100.vtk` — **not in the repo**; used by `ml-dvr`, `ml-iso`, `ml-slice-iso`. Source it separately or those three scenarios fail at `LegacyVTKReader`.
- The notebooks reference the old macOS path for these files, not `data/benchmark/`. You will need to edit the paths.

## `chatvis/` package — current state (WIP, do not assume working)

- `code_examples.py` exposes `CODE_EXAMPLES: list[CodeExample]` and a derived `CODE_EXAMPLES_DF` DataFrame. Code snippets use placeholders like `<input_path>`, `<output_path>` (angle-bracket sentinels, not `str.format` fields).
- `prompts.py` exposes `PROMPT_EXAMPLES`, `LLM_PROMPTS` (`string.Template` with `$input_path`/`$output_path`), and `CODE_GENERATION_PROMPTS`. **Note**: the `CodeGenerationPrompt` `system_prompt` contains `{code_to_read}`, `{code_to_slice}`, etc. as plain-string literals — nothing in the current codebase calls `.format(**...)` on them, so they will appear verbatim if sent to an LLM. This is unfinished, not a bug to "fix" silently.
- `utils.py` `extract_python_code` returns a `list[str]` (different signature from the notebook version). Has the iterate-and-append bug noted above.
- `main.py` CLI accepts `--scenario` and `--model gpt4o`; all match arms are `pass`. Running `python -m chatvis.main` does nothing.

## Working on this repo

- "Verification" = run the relevant notebook end-to-end against `pvpython` and visually compare the generated screenshot to `data/benchmark/<scenario>/<scenario>-screenshot.png`. There is no automated test step.
- When changing a helper that exists in multiple notebooks (`extract_python_code`, `extract_error_messages`, the `code_to_*` snippets), apply the same edit to every notebook that has it. Do not consolidate into a shared module without explicit request.
- If you're porting a notebook into `chatvis/`, the existing extraction pattern (`CodeExample`/`PromptExample` Pydantic models in `chatvis/`) is the direction of travel — follow it.
- Avoid `jq` / raw-JSON edits to `.ipynb` files. Use Jupyter or `nbconvert` and understand the cell schema first.

## Existing docs

- `README.md` covers only the end-user "install jupyter, paste key, run cells" flow. It does not mention the package, `uv`, pre-commit, the hard-coded paths, the `ollama` dead import, the missing `ml-100.vtk`, or the per-notebook differences above.
