# AGENTS.md

Research artifact accompanying the ChatVis paper. Five standalone Jupyter notebooks at the repo root, each a near-duplicate scaffold that drives the OpenAI API + `pvpython` to iteratively generate a ParaView visualization script. No package, no tests, no CI, no manifest.

## Layout

- `*.ipynb` (root): one notebook per scenario — `ml-dvr`, `ml-iso`, `ml-slice-iso`, `points-surf-clip`, `stream-glyph`. Each is self-contained; treat them as siblings, not modules.
- `ground truth examples/<scenario>/`: reference `prompt.txt`, hand-written `*.py`, expected screenshot, and (for two scenarios) the input dataset (`disk.ex2`, `can_points.ex2`).
- `generated scripts/<scenario>/`: committed sample of one prior generated script + its screenshot. **Folder naming is inconsistent**: `generated scripts/stream_glyph/` (underscore) vs `ground truth examples/stream-glyph/` (hyphen). Do not "normalize" without asking.
- The other three scenarios (`ml-dvr`, `ml-iso`, `ml-slice-iso`) all use `ml-100.vtk`, which is **not** in the repo — see Datasets below.

## Runtime requirements (not in any manifest)

- Python 3.12 kernel (`ipykernel`).
- `pip install jupyter openai ollama` — `ollama` is imported by `ml-dvr`, `ml-iso`, `ml-slice-iso` but never actually called; import will fail without the package even though it is dead code.
- ParaView 5.12 providing `pvpython` on `PATH`. Notebooks hard-code a macOS path: `path_to_pvpython = "/Applications/ParaView-5.12.0.app/Contents/bin:$PATH"` and append it to `os.environ["PATH"]`. On Linux this line is a no-op; ensure `pvpython` is otherwise resolvable.
- An OpenAI API key. Notebooks have **no env var loading** — you must paste the key directly into `OpenAI(api_key="")`. Do not commit it.

## Hard-coded absolute paths (CRITICAL)

Every notebook bakes the original author's macOS paths into both the saved-script location and the prompts sent to the LLM:

- Output dir: `/Users/tanwimallick/Documents/Paraview/generated_code/` — used by `extract_python_code` to write generated `*.py`, and embedded in the `user_input` / `exapmle_input` prompt strings as the input data path and the screenshot save path.
- Input data paths in prompts (e.g. `'/Users/tanwimallick/Documents/Paraview/generated_code/ml-100.vtk'`, `disk.ex2`, `can_points.ex2`).

To make a notebook runnable elsewhere you must edit **all three** places per notebook (the `extract_python_code` filename, the `user_input` data path, and the `SaveScreenshot` path inside `code_to_save`). The committed `ground truth examples/*/prompt.txt` files use a different absolute path (`/Users/tpeterka/collaborations/tanwi/examples/...`) — they are reference text, not used at runtime.

## Datasets

- `disk.ex2` and `can_points.ex2` ship under `ground truth examples/`.
- `ml-100.vtk` (used by three notebooks) is **not** in the repo. Source it separately before running those notebooks, or the generated script will fail at `LegacyVTKReader`.

## Per-notebook quirks

- **`stream-glyph.ipynb`** is the only notebook with an active LLM error-correction loop (`while errors:`). Uses `gpt-4` for both generation and repair.
- **`ml-dvr.ipynb`**, **`points-surf-clip.ipynb`**: the `while errors:` loop is commented out — they run exactly one generation attempt. Uses `gpt-4o` for prompt generation, `gpt-4-turbo` for code generation.
- **`ml-iso.ipynb`** has a **duplicated** `subprocess.run` / `extract_error_messages` block (lines run twice with no loop). Likely a copy-paste bug; preserve behavior unless explicitly asked to fix.
- **`extract_python_code`** has `return filename` **inside** the `for` loop, so only the first ```python``` block in the LLM response is ever saved. Known limitation across all notebooks.

## Working on this repo

- Notebooks are committed **with output cells** (large base64 PNGs). Re-running a notebook will rewrite execution counts and outputs; check `git diff` carefully before committing — ask whether the user wants outputs included.
- There is no lint, format, typecheck, or test step. "Verification" means running the notebook end-to-end against ParaView and visually comparing the generated screenshot to `ground truth examples/<scenario>/*-screenshot.png`.
- The five notebooks share ~90% of their code (helpers, primer snippets like `code_to_read`, `code_to_slice`, etc.). When changing a helper, apply the same edit to every notebook that has it — do not refactor into a shared module unless the user asks; the per-notebook duplication is intentional for the paper's reproducibility.
- Use `nbconvert` or open in Jupyter to inspect/edit. Avoid `jq`-based in-place edits to `.ipynb` JSON unless you understand the cell schema.

## Existing docs

- `README.md` covers only the end-user "install jupyter, paste key, run cells" flow. It does not mention the hard-coded paths, the `ollama` dead import, the missing `ml-100.vtk`, or the per-notebook differences above.
