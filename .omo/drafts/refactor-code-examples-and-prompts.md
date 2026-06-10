# Draft: Refactor chatvis/code_examples.py and chatvis/prompts.py to support notebooks

## Original Request

> Review notebooks/, chatvis/code_examples.py, and chatvis/prompts.py. Identify areas
> where we can refactor chatvis/code_examples.py and chatvis/prompts.py to better
> support the code examples, prompt generation, and code generation prompts leveraged
> in notebooks/. Write new base classes and helper functions to properly capture the
> data. Please ask questions.

## Confirmed facts from investigation (notebooks + package, verbatim)

### Notebook structure per scenario

Each notebook follows roughly this skeleton (some steps omitted in some files):

1. `extract_python_code(text, name) -> filename` and `extract_error_messages(stderr) -> list[str]`.
2. A set of `code_to_*` triple-quoted snippets, scoped to that notebook's needs.
3. `exapmle_input`, `exapmle_prompt`, `user_input` strings (typos preserved in code).
4. **(Optional)** Prompt-generation LLM call → `prompt = chat_completion.choices[0].message.content`.
5. Code-generation LLM call with a system prompt that interpolates `{code_to_*}` snippets via f-string, user content = `prompt` (or `user_input` directly).
6. `extract_python_code(script, '<scenario>') -> file_path`.
7. `subprocess.run(["pvpython", file_path], capture_output=True, text=True).stderr` →
   `extract_error_messages` → `errors`.
8. **(Optional)** `while errors:` repair loop that re-prompts the LLM with the error
   text + previous script + original user prompt, then re-runs pvpython.

### Per-scenario differences (must be preserved)

| Scenario          | Has prompt-gen step? | Prompt-gen model | Code-gen model | Repair loop  | Repair model | code_to_* snippets used                                                                                                                                                  |
|-------------------|----------------------|------------------|----------------|--------------|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ml-dvr            | YES                  | gpt-4o           | gpt-4-turbo    | COMMENTED    | gpt-4        | read, slice, contour, clip, color_transfer_function, opacity_transfer_function, render_view, render_view_direction, isometric_view, contour1Display, create_layout, save |
| ml-iso            | YES                  | gpt-4o           | gpt-4-turbo    | NONE (block duplicated instead) | n/a | read, slice, contour, clip, render_view, render_view_direction, isometric_view, contour1Display, create_layout, save |
| ml-slice-iso      | YES                  | gpt-4-turbo      | gpt-4o         | NONE         | n/a          | same as ml-iso                                                                                                                                                            |
| points-surf-clip  | NO (prompt inlined)  | n/a              | gpt-4-turbo    | ACTIVE       | gpt-4        | read, slice, contour, render_view (camera-explicit variant), contour1Display, create_layout                                                                              |
| stream-glyph      | NO (prompt inlined)  | n/a              | gpt-4          | ACTIVE       | gpt-4        | read, slice, contour, render_view, render_view_direction, isometric_view, contour1Display, create_layout, save, clip, stream_tacer (typo), glyph, tube, color_tube_glyphs_Temp_variable |

### Repair-loop system prompt variants

- `ml-dvr` (commented-out): `"You are a code assistant."`
- `points-surf-clip`, `stream-glyph` (active): `"You are a great code assistant. Focus on the error line. Dont change the entire code"`

### Repair-loop user prompt variants

- `ml-dvr` (commented): `f"I encountered a Python error:\n{errors}\n Can you fix the code \n{script}\n and write a new script?"`
- `points-surf-clip`: `f"I encountered a Python error:\n{errors}\n Can you fix the code \n{script}\n and write a new script for the user \n{prompt}\n ?"`
- `stream-glyph`: `f"I encountered a Python error:\n{errors}\n Can you fix the code \n{script}\n  for the user \n{prompt}\n ?"` (two spaces after `\n`)

### Known string-level discrepancies vs `chatvis/code_examples.py` / `chatvis/prompts.py`

- **`code_to_stream_tacer` (notebook typo) vs `code_to_stream_tracer` (package, corrected)** — same content, different name. Affects only stream-glyph.
- **`code_to_render_view`** — points-surf-clip notebook adds explicit `CameraPosition`/`CameraFocalPoint`/`CameraViewUp` lines; package's version is the simple one used by every other notebook. The two variants are not interchangeable.
- **`code_to_save`** — notebooks hard-code a literal `/Users/tanwimallick/Documents/Paraview/generated_code/points-surf-clip-screenshot.png` (yes, even ml-dvr uses the points-surf-clip path; this is a notebook copy-paste bug). Package uses `<output_path>` sentinel.
- **`code_to_clip`** — notebook versions (e.g. ml-iso) omit the `from paraview.simple import *` header that the package version includes. Other snippets have the same drift: package adds the import line; some notebooks do, some don't.
- **`prompts.py` placeholder typo**: `ml_iso` `generated_prompt` references `<ouput_path>` (sic). `ml_slice_iso` `generated_prompt` uses `<input_file>` / `<output_file>` instead of `<input_path>` / `<output_path>`.
- **`prompts.py` placeholders never substituted**: `CODE_GENERATION_PROMPTS[0].system_prompt` contains `{code_to_read}`, `{code_to_save}`, etc. as plain-string literals — nothing calls `.format()` on them. Also only the `ml_dvr` variant exists; the other four scenarios' code-gen system prompts are missing entirely.
- **`PROMPT_EXAMPLES` semantics drift**: each scenario's `input_prompt` / `generated_prompt` describes the **stream-glyph** task (streamlines + tubes + glyphs + Temp coloring), but is labeled with the target scenario's name. The notebooks always pass the *stream-glyph* example as the few-shot exemplar to the prompt-generator regardless of target scenario; the package mirrors that, but the `name` field is misleading.
- **`extract_python_code`** — notebook version `(text, name) -> filename`, returns after first block (early-return bug). Package version `(text) -> list[str]`, but appends to the same list it iterates (duplication bug). Neither is correct.

## Refactor scope inferred (NEEDS USER CONFIRMATION)

The data needed by the notebooks decomposes naturally into:

1. **Reusable ParaView snippet library** (`code_examples.py`):
   - A `CodeExample` value with `name`, `code`, and a small amount of metadata
     (which placeholder sentinels it contains, e.g. `<input_path>`, `<output_path>`).
   - A registry / lookup helper so prompts can pull snippets by name.

2. **Per-scenario configuration** (probably new `scenarios.py` or expanded `prompts.py`):
   - `name`, `dataset_path`, `output_screenshot_path`.
   - `prompt_generation: PromptGenerationStep | None` (None for points-surf-clip,
     stream-glyph).
   - `code_generation: CodeGenerationStep` — refers to a list of code-example
     names and a template that interpolates them.
   - `repair: RepairStep | None` — system prompt, user-prompt template, model.
   - `models: dict[str, str]` or three explicit fields capturing the
     prompt-gen / code-gen / repair model overrides.

3. **Prompt templates** that *actually substitute*:
   - Switch from `str.format` + plain strings to `string.Template` with explicit
     `${input_path}` / `${output_path}` / `${example_user_prompt}` /
     `${example_generated_user_prompt}`, AND a helper that fills the
     `${code_to_*}` slots from the snippet registry.
   - A `render(template, *, code_snippets: dict[str, str], **kwargs) -> str`
     helper would close the gap.

4. **Few-shot example** (the stream-glyph user-prompt / generated-prompt pair) as
   a single shared `FewShotExample` rather than duplicated per scenario.

5. **Validation helpers**:
   - Assert every `{code_to_*}` referenced by a `CodeGenerationStep.template` is
     present in the snippet registry.
   - Assert every placeholder (`<input_path>`, `<output_path>`,
     `${example_user_prompt}`, …) is supplied at render time.

## Open questions to resolve before planning

(Asked in interview below — see Open Questions section in the chat.)

## Decisions

- **Normalize bugs, update notebooks**: package becomes source of truth. Fix typos
  (`exapmle_*`, `<ouput_path>`, `code_to_stream_tacer`), the wrong-screenshot-path
  in `code_to_save`, the `extract_python_code` early-return / duplicate-append
  bugs, the wrong scenario-named `PROMPT_EXAMPLES`. Notebooks will be rewritten
  to import from `chatvis/`. Past LLM byte-identical reproduction is NOT a goal.
- **`Scenario` Pydantic model per notebook**: bundles dataset path, expected
  screenshot path, prompt-generation step (optional), code-generation step,
  repair step (optional), and model choices. `chatvis/main.py` match arms
  dispatch to `scenario.run()`.
- **`string.Template` everywhere**: Convert every snippet and prompt to
  `string.Template`. Code snippets get rewritten so `<input_path>` becomes
  `${input_path}`. Validation uses `Template.get_identifiers()`. Single
  `render(template, *, snippets, **vars) -> str` helper.
- **Single shared `FewShotExample`**: One `FEWSHOT_EXAMPLE` based on the
  stream-glyph pair. Every `Scenario.prompt_generation` references it. Drop the
  four duplicate `PROMPT_EXAMPLES` entries.
- **Enable repair loop for all five scenarios** uniformly. Use the
  points-surf-clip / stream-glyph repair system prompt verbatim
  (`"You are a great code assistant. Focus on the error line. Dont change the entire code"`).
  Add a default max-iteration cap (TBD — ask user).
- **Fix `chatvis/utils.py` too**: correct `extract_python_code` to return
  `list[str]` without the duplicate-append bug, keep
  `extract_error_messages` signature (improve typing), add
  `run_pvpython(script_path) -> tuple[int, str, str]`.
- **Default model = `gpt-4o`** for every step. Each `Scenario` can override
  per-step via `models: dict[str, str]` (keys: `prompt_generation`,
  `code_generation`, `repair`).
- **Parameterized `code_to_render_view` via free-form `${...}` slots**: every
  snippet uses `string.Template`, including `${camera_position}`,
  `${camera_focal_point}`, `${camera_view_up}` on render-view snippets. Caller
  passes pre-formatted strings. No subclasses, uniform registry.
- **Repair cap**: `Scenario.repair.max_iterations: int = 5`, overridable.
- **Verification**: add `pytest` as a dev dep. Unit tests for snippet registry,
  template rendering, placeholder validation, `extract_python_code` (golden
  multi-block cases), `extract_error_messages`, `Scenario` construction. Mock
  OpenAI client \u2014 no live calls.

## Scope boundaries

### IN
- `chatvis/code_examples.py` rewrite
- `chatvis/prompts.py` rewrite
- New `chatvis/scenarios.py` with `Scenario` Pydantic model + five scenario constants
- `chatvis/utils.py` bug fixes + `run_pvpython` helper
- New `tests/` directory with pytest suite (unit + render-golden snapshots)
- `pyproject.toml` dev dep: add `pytest`
- Minimal wiring update in `chatvis/main.py` to dispatch via `SCENARIOS[name].run()`
  (where `run()` is a thin orchestrator; we can keep it `NotImplementedError` for
  the actual OpenAI call if `llm.py` is still empty \u2014 decide in plan)

### OUT
- Rewriting notebooks to import from `chatvis/` (separate plan)
- Implementing `chatvis/llm.py` (still entirely commented out; leave for follow-up
  unless tests force a minimal client interface)
- Live OpenAI API calls in any test
- CI workflow setup
- Modernizing `.pre-commit-config.yaml` python3.13 \u2192 3.14 mismatch (separate concern)
