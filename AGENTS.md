# AGENTS.md

Research artifact for the ChatVis paper (LLM-driven ParaView script generation). **Two implementations coexist:** original Jupyter notebooks under `notebooks/` (reference behavior preserved for the paper) and a Python package under `chatvis/` (active migration). Notebook behavior is the source of truth; package code is the direction of travel.

## Current repo state (read this first)

- The package pipeline is **wired end-to-end** through `chatvis/main.py`. `python -m chatvis.main --help` works; `python -m chatvis.main --scenario <s> --data-filepath <p> --screenshot-path <p> --username <anl-id>` will execute prompt-improvement → code-generation → script extraction → `pvpython` → bounded repair loop.
- The old `chatvis/documents/` package has been removed. All prompt/data sources now live under `chatvis/v1/`. Do not re-add `chatvis/documents/`.
- The notebooks under `notebooks/` are unchanged and remain the paper reference. The package is a reimplementation, not a refactor: it does not import notebook code and is not expected to be byte-identical to it.
- Live verification against Argonne's Argo endpoint has **not** been run from this assistant — it requires an ANL username. The orchestrator has been exercised end-to-end with a stubbed LLM and a real `pvpython`-style subprocess; the LLM wire format has not been independently confirmed against Argo.

## Running the package pipeline

End-to-end example (Linux, `pvpython` on `PATH`):

```bash
uv run python -m chatvis.main \
    --scenario stream-glyph \
    --data-filepath data/disk.ex2 \
    --screenshot-path /tmp/stream-glyph.png \
    --username <your-anl-id>
```

The orchestrator derives the script path from `--screenshot-path` by replacing the suffix with `.py` (e.g. `/tmp/stream-glyph.py`), so generated script and screenshot land side-by-side. Override `pvpython` with `--pvpython /path/to/pvpython` if the wrong one is on `PATH`; bound repair attempts with `--max-repair-attempts N` (default `5`). Add `--log-file` to also tee logs to `chatvis_<unix-seconds>.log` in the cwd.

Per-scenario verification of a successful run is currently manual:

1. Confirm `python -m chatvis.main ... --username <anl-id>` exits `0`.
2. Open the generated `<screenshot-path>` and visually compare with the corresponding `notebooks/` reference.
3. Inspect the generated `<screenshot-path>.with_suffix('.py')` against the notebook's saved script for major divergence.

There is no automated screenshot diff. Local `pvpython` may also be a different ParaView major version than the 5.12 the notebooks were authored against (e.g. this machine runs 6.1.1); some snippets in `chatvis/v1/documents/code.py` may need updating to match. Flag any failing scenario in a follow-up rather than editing snippets ad-hoc inside an orchestrator session.

## Layout

- `chatvis/` — installable package (Python 3.14).
    - `__init__.py`, `cli.py`, `main.py`, `llm.py`, `utils.py`, `logger.py` — top-level orchestration.
        - `cli.py` — `argparse` setup. CLI flags: `--scenario`, `--data-filepath`, `--screenshot-path`, `--model` (only `gpt4o` today), `--username` (Argo auth), `--endpoint`, `--pvpython` (default `shutil.which("pvpython")`), `--max-repair-attempts` (default `5`), `--log-file`, `--log-level`.
        - `main.py` — orchestrator. `run_pipeline()` runs the four stages and the bounded repair loop; `check_data()` validates `--data-filepath` exists and warns on scenario↔file mismatch. Exit codes: `0` clean run, `1` repair-loop exhausted (or no python block returned), `2` pre-flight configuration error.
        - `llm.py` — `OpenAIModel` (reproducible defaults: `seed=42`, `temperature=0.0`, `top_p=1.0`, `n=1`); `improve_prompt`, `generate_code`, `improve_code` are the three LLM-call helpers; `parse_response`, `_substitute_paths`, `_FEW_SHOT_KEY_BY_SCENARIO` (binary toggle between the two example families so the few-shot is never self-referential).
        - `utils.py` — `extract_python_code(text) -> list[str]` returns every fenced `python` block; `extract_error_messages(stderr) -> list[str]` anchors on `Traceback (most recent call last):` so VTK's ANSI-coloured warnings don't register as Python errors.
        - `logger.py` — `configure_logging(log_to_file, level)` installs handlers on the `chatvis` root logger with UTC timestamps; returns the log file path or `None`.
    - `chatvis/v1/` — **canonical active target** for the refactor. Tracked. Edit here.
        - `v1/script.py` — `derive_script_path(screenshot_path)` (replaces suffix with `.py`), `first_python_block(llm_response)` (raises `ValueError` if no fenced block; debug-logs when discarding extras), `write_script(code, path)` (creates parent dirs, returns the path).
        - `v1/pvpython.py` — `run_pvpython(pvpython_path, script_path)`. Pre-flight validates the binary exists and is executable and that the script exists, before spawning. `check=False`; the orchestrator treats the presence of an extracted traceback as the failure signal, not the return code.
        - `v1/documents/code.py` — `CodeSnippet(StrEnum)`: ParaView code examples used as LLM context. Snippets contain angle-bracket sentinels (`<input_path>`, `<output_path>`) intended for **LLM** substitution, not Python `str.format`.
        - `v1/documents/prompts.py` — `GeneratedPrompt(StrEnum)`: per-scenario input/output prompt pairs. Module-level `_COMMON_INPUT`/`_COMMON_OUTPUT` constants are intentionally shared by the stream-glyph family (`ML_DVR`, `ML_ISO`, `ML_SLICE_ISO`, `STREAM_GLYPH`); `POINTS_SURF_CLIP_*` is the only distinct pair. Sentinels here (`<input_path>`, `<output_path>`) are substituted by `chatvis.llm._substitute_paths` because we own these strings.
        - `v1/prompts/{code_generation,code_improvement,prompt_improvement}.py` — `StrEnum`s with `SYSTEM_PROMPT` and `USER_PROMPT` members. **v1 prompts use Python `str.format` placeholders** (`{user_input}`, `{example_user_input}`, `{example_user_output}` for prompt improvement; `{prompt}` for code generation; `{errors}`, `{script}`, `{prompt}` for code improvement). The deleted `chatvis/documents/` used `string.Template` (`$name`). Do not mix the two.
- `notebooks/` — five scenario notebooks: `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`. ~90% near-duplicate scaffolds; duplication is **intentional for paper reproducibility** — do not refactor into a shared module without asking.
- `data/` — flat layout, three files only: `ml-100.vtk`, `disk.ex2`, `can_points.ex2`. Notebooks still hard-code macOS author paths (not `data/`); edit when running locally.
- `dist/`, `chatvis.egg-info/`, `.ruff_cache/` — build/tool artifacts; do not commit.

## Toolchain (Python 3.14, uv-managed)

- `pyproject.toml` requires `python>=3.14`; `.python-version` pins `3.14`. `.venv/` at repo root is the working env.
- **Pre-commit pins Python 3.13** (`.pre-commit-config.yaml:2`: `default_language_version: python: python3.13`) even though the project targets 3.14. Hooks run under 3.13. Do not "fix" without confirming.
- Pre-commit hook order: `pre-commit-hooks` → `isort` → `ruff-format` → `ruff-check` → `bandit` → **local `prettier`** (uses system-installed `prettier`; will fail if not on PATH). Run via `pre-commit run --all-files`. No separate `make lint` target.
- `[tool.isort]` is set to `profile = "black"`, `line_length = 88` so isort doesn't fight ruff-format's wrapping. No `[tool.ruff]` config — ruff runs on defaults.
- `pytest>=9.0.3` is a declared dev dep, but **there is no `tests/` directory and no test files anywhere**. Don't assume a test suite exists.
- No CI workflows.
- Dependencies: `openai>=2.41`. Dev: `jupyter>=1.1.1`, `pytest>=9.0.3`. (`pydantic` is still installed transitively via `openai`; the v1 package code is `StrEnum`-based and does not import it directly. `pandas` was removed alongside the unused `pydantic_to_dataframe` helper.)
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
- `check_data` in `chatvis/main.py:70` is the authoritative scenario↔file mapping (driven by `_EXPECTED_DATA_BY_SCENARIO`). Mismatches are warnings, not errors — the LLM never inspects the file. Notebooks still reference old macOS paths, not `data/`.

## Working on this repo

- "Verification" of a scenario = run the notebook (or, eventually, the package CLI) end-to-end against `pvpython` (ParaView 5.12) and visually compare the generated screenshot to the reference. There is no automated test step.
- When changing a helper duplicated across notebooks (`extract_python_code`, `extract_error_messages`, the `code_to_*` snippets), apply the same edit to every notebook that has it. Do not consolidate without explicit request.
- Avoid `jq` / raw-JSON edits to `.ipynb` files. Use Jupyter or `nbconvert` and understand the cell schema first.
- `README.md` covers only the legacy notebook flow (install jupyter, paste key, run cells). It does not mention the package, `uv`, pre-commit, Argo, the hard-coded paths, the migration to `chatvis/v1/`, or any of the gotchas here. Treat this `AGENTS.md` as authoritative when they conflict.
