# AGENTS.md

Research artifact for the ChatVis paper (LLM-driven ParaView script generation). **Two implementations coexist:** original Jupyter notebooks under `notebooks/` (reference behavior preserved for the paper) and a Python package under `chatvis/` (active migration). Notebook behavior is the source of truth; package code is the direction of travel.

## Current repo state (read this first)

- Branch: `dev`, ahead of `origin/dev` by 1 commit at last check.
- **`chatvis/documents/` has been deleted (uncommitted `git rm`).** Run `git status` to confirm. The directory was the old prompt/data home and is being replaced by `chatvis/v1/`.
- **`chatvis.main` is broken at import time right now:** `chatvis/main.py:10` and `chatvis/llm.py:7-9` still `from chatvis.documents.* import ...`. Those modules no longer exist on disk. `python -m chatvis.main` will fail with `ModuleNotFoundError` before parsing any args. Do not "fix" this casually — confirm with the user whether the imports should be repointed to `chatvis.v1.*` or whether `chatvis/documents/` should be restored. The migration is mid-flight.
- `chatvis/main.py:113` also calls `cli_parser()`, which does not exist (`chatvis/cli.py` exports a `CLI` class with a `parser()` method). Separate bug from the above, also unresolved.

## Layout

- `chatvis/` — installable package (Python 3.14).
    - `__init__.py`, `cli.py`, `llm.py`, `main.py`, `utils.py`, `logger.py` — top-level orchestration.
    - `chatvis/v1/` — **canonical active target** for the refactor. Tracked. Edit here.
        - `v1/documents/code.py` — `CodeSnippet(StrEnum)`: ParaView code examples used as LLM context. Snippets contain angle-bracket sentinels (`<input_path>`, `<output_path>`) intended for LLM substitution, not Python `str.format`.
        - `v1/documents/prompts.py` — `GeneratedPrompt(StrEnum)`: per-scenario input/output prompt pairs. **Known data bug:** every `*_INPUT` value other than `POINTS_SURF_CLIP_INPUT` contains the streamline/glyph text — they are copy-paste duplicates of `STREAM_GLYPH_INPUT`. The `*_OUTPUT` values are also wrong for several scenarios. Verify before relying on any non-stream-glyph entry.
        - `v1/prompts/{code_generation,code_improvement,prompt_improvement}.py` — `StrEnum`s with `SYSTEM_PROMPT` and `USER_PROMPT` members. **v1 prompts use Python `str.format` placeholders (`{prompt}`, `{errors}`, `{script}`).** The deleted `chatvis/documents/` used `string.Template` (`$name`). Do not mix the two.
- `notebooks/` — five scenario notebooks: `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`. ~90% near-duplicate scaffolds; duplication is **intentional for paper reproducibility** — do not refactor into a shared module without asking.
- `data/` — flat layout, three files only: `ml-100.vtk`, `disk.ex2`, `can_points.ex2`. Notebooks still hard-code macOS author paths (not `data/`); edit when running locally.
- `dist/`, `chatvis.egg-info/`, `.ruff_cache/` — build/tool artifacts; do not commit.

## Toolchain (Python 3.14, uv-managed)

- `pyproject.toml` requires `python>=3.14`; `.python-version` pins `3.14`. `.venv/` at repo root is the working env.
- **Pre-commit pins Python 3.13** (`.pre-commit-config.yaml:2`: `default_language_version: python: python3.13`) even though the project targets 3.14. Hooks run under 3.13. Do not "fix" without confirming.
- Pre-commit hook order: `pre-commit-hooks` → `isort` → `ruff-format` → `ruff-check` → `bandit` → **local `prettier`** (uses system-installed `prettier`; will fail if not on PATH). Run via `pre-commit run --all-files`. No separate `make lint` target.
- No `[tool.ruff]` config — ruff runs on defaults.
- `pytest>=9.0.3` is a declared dev dep, but **there is no `tests/` directory and no test files anywhere**. Don't assume a test suite exists.
- No CI workflows.
- Dependencies: `openai>=2.41`, `pandas>=3.0.3`, `pydantic>=2.13.4`. Dev: `jupyter>=1.1.1`, `pytest>=9.0.3`. (Pydantic was used by the deleted `chatvis/documents/`; v1 is `StrEnum`-based and does not import pydantic.)
- `Makefile`:
    - `make create-dev` → `pre-commit install && pre-commit autoupdate && rm -rf env && uv sync`
    - `make build` → derives version from `git tag | … | tail -n 1 | xargs -I % uv version %`, then `uv build`, then `uv pip install dist/*.tar.gz`. **There are no git tags**, so `make build` passes an empty version to `uv version` and fails. Tag first or skip.
- Notebooks are committed **with output cells** (large base64 PNGs). Re-running rewrites execution counts and outputs — inspect `git diff` carefully and ask before committing notebook output churn.

## Package conventions (active in `chatvis/v1/`)

- All prompt/code sources are `enum.StrEnum`s under `chatvis/v1/`. No Pydantic in v1.
- Prompt templates use Python `str.format` (`{name}`). Format-time substitution happens at the call site.
- Code snippets in `CodeSnippet` use angle-bracket sentinels (`<input_path>`, `<output_path>`) intended for the LLM to substitute, not Python.
- `SYSTEM_PROMPT` in `v1/prompts/code_generation.py` embeds each `CodeSnippet` value inside a Markdown fenced code block where the "language" slot is a short natural-language description of the snippet (e.g. ` ```create a slice filter `). When extending, preserve this pattern.
- The package targets **Argonne's Argo API** — an OpenAI-compatible endpoint, `DEFAULT_ENDPOINT = "https://apps.inside.anl.gov/argoapi/v1"` (`chatvis/cli.py:9`). Authentication is by ANL username passed as `api_key` to the OpenAI `Client` (see comment in `chatvis/llm.py:21-22`). **Not** plain OpenAI. Do not add `OPENAI_API_KEY` loading.
- `--model` choices are restricted to `["gpt4o"]` (`chatvis/cli.py:6`).
- Logging: every submodule should use `logging.getLogger(__name__)`. `chatvis/logger.py` configures the `chatvis` root logger and disables propagation.
- When porting more notebook behavior, follow the migration target: data in `chatvis/v1/documents/`, prompt strings in `chatvis/v1/prompts/`, orchestration in `chatvis/llm.py` and `chatvis/main.py`.

## Notebook gotchas (all five files, still present)

- **Hard-coded macOS author paths** in every notebook in three places: `extract_python_code` output filename, the `user_input` prompt text (input dataset path), and the `SaveScreenshot` path inside `code_to_save`. All point at `/Users/tanwimallick/Documents/Paraview/generated_code/`. Edit **all three** per notebook to run elsewhere.
- **macOS-only `pvpython` path** prepended to `PATH`: `"/Applications/ParaView-5.12.0.app/Contents/bin:$PATH"`. No-op on Linux; ensure `pvpython` (ParaView 5.12) is otherwise on `PATH`.
- **`OpenAI(api_key="")`** in the notebooks — no env-var loading. Paste key directly; do not commit. (The package code path uses Argo and `--username`, not this.)
- **Dead `import ollama`** in `ml-dvr.ipynb`, `ml-iso.ipynb`, `ml-slice-iso.ipynb` (never called). Notebook will `ImportError` without `pip install ollama` even though removing the import would also work. `ollama` is NOT in `pyproject.toml` deps.
- **`extract_python_code` early-return bug in the notebooks**: `return filename` sits inside the `for` loop, so only the first `python` block from the LLM response is ever saved. Present in all five. The package version in `chatvis/utils.py:11` has a different, correct implementation that returns `list[str]` — do not assume parity.

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
- `check_data` in `chatvis/main.py:36` is the authoritative scenario↔file mapping. Notebooks still reference old macOS paths, not `data/`.

## Working on this repo

- "Verification" of a scenario = run the notebook (or, eventually, the package CLI) end-to-end against `pvpython` (ParaView 5.12) and visually compare the generated screenshot to the reference. There is no automated test step.
- When changing a helper duplicated across notebooks (`extract_python_code`, `extract_error_messages`, the `code_to_*` snippets), apply the same edit to every notebook that has it. Do not consolidate without explicit request.
- Avoid `jq` / raw-JSON edits to `.ipynb` files. Use Jupyter or `nbconvert` and understand the cell schema first.
- `README.md` covers only the legacy notebook flow (install jupyter, paste key, run cells). It does not mention the package, `uv`, pre-commit, Argo, the hard-coded paths, the migration to `chatvis/v1/`, or any of the gotchas here. Treat this `AGENTS.md` as authoritative when they conflict.
