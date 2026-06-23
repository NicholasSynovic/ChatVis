# ChatVis v3 — OpenCode agent/skill experiments

`chatvis/v3/` is **not a pipeline.** Unlike `v1` and `v2`, nothing in
`chatvis/*.py` imports or references anything here, there is no
`run_v3_pipeline`, and `v3` is not a CLI subcommand. It is a pair of
OpenCode-native artifacts — a **subagent** and a **skill** — that re-express
ChatVis's "improve the prompt, then generate a ParaView script" workflow as
composable agent primitives instead of a monolithic Python orchestrator.

Two tracked components live here:

- `agents/paraview-prompt-formatter.md` — an OpenCode **subagent** that shapes a
  casual visualization request into a precise ParaView prompt.
- `skills/paraview-coder/` — an OpenCode **skill** that turns such a prompt into
  a complete headless `pvpython` script.

## `agents/paraview-prompt-formatter.md`

An OpenCode **subagent** (`mode: subagent`) with **every tool permission set to
`deny`** — it is a pure text transform with no side effects (no file reads, no
shell, no web). It turns a casual, vague, or under-specified natural-language
visualization request into a precise, flat-prose ParaView prompt that a
downstream script generator can execute.

Behavior:

- **Blocks on the two required paths** — the input data file and the output
  screenshot path. If either is missing it asks the user and emits no final
  prompt until both are supplied; it never invents paths.
- **Preserves every concrete value verbatim** — file paths, numeric values
  (isosurface values, thresholds, coordinates), array/variable names, axis
  directions, colors.
- **Maps casual terms to ParaView operations** — e.g. "cross-section" → Slice,
  "level set" → Contour, "flow lines" → StreamTracer, "arrows" → Glyph.
- **Bakes in conventions** unless overridden — save a screenshot, render at
  1920 x 1080 — and **orders operations in pipeline order** (source before
  dependent filters).
- **Emits only the prompt** (plus an optional `Notes:` block), and ships three
  few-shot examples (isosurface; streamlines with glyphs and coloring;
  Delaunay + clip + wireframe).

## `skills/paraview-coder/`

An OpenCode **skill** (`SKILL.md` plus reference catalogs and evals) whose job
is to write **one** complete Python script that runs under `pvpython` and saves
a screenshot to disk. It encodes the headless realities of `pvpython`: there is
no interactive window, so the script must build the whole pipeline, frame the
camera explicitly, and save an image — nothing is implicit.

- **`SKILL.md`** — the entry point. Defines: - the **output contract**: return the script as a single fenced `python`
  block (downstream tooling extracts the _first_ python block), beginning
  with `from paraview.simple import *`; - the **placeholder substitution** rules — `<input_path>`, `<output_path>`,
  and the placeholder scalar array name `'var0'` — the same sentinel
  convention used by the v1/v2 snippet corpora; - an **8-step workflow** (reader → optional data inspection → filters →
  render view → display & color → layout/extra views → camera framing →
  output); and - a **Gotchas** section distilled from observed `pvpython` failure modes:
  blank screenshots from an unframed or hand-rolled camera, `Contour array
is null` from a leftover `'var0'`, solid-black volume renders from
  incomplete transfer functions, the `LowerThreshold`/`UpperThreshold` vs.
  `ThresholdRange` API drift, and more.
- **`references/`** — six load-on-demand snippet catalogs, each a categorized
  list of working snippets with a one-line "use when". `SKILL.md` instructs the
  agent to open only the files a given request needs:
    - `readers.md` — readers by extension + data inspection (204 lines).
    - `filters.md` — slice, contour, clip, glyph, stream tracer, tube,
      calculator, threshold, Delaunay, etc. (409 lines).
    - `displays-and-color.md` — representations, coloring, transfer functions,
      volume rendering, scalar bars (182 lines).
    - `rendering-and-camera.md` — render views and camera framing (141 lines).
    - `layout-and-views.md` — layouts, side-by-side, chart/histogram views,
      annotations (99 lines).
    - `output.md` — screenshots, data/mesh export, animations, state (111
      lines).
- **`evals/evals.json`** — three eval scenarios that map directly onto the
  repository's canonical scenarios and datasets: `stream-glyph-tubes`
  (`data/disk.ex2`), `isosurface-named-array` (`data/ml-100.vtk`), and
  `points-clip-wireframe` (`data/can_points.ex2`). The sibling
  `skills/paraview-coder-workspace/` directory (when present) holds eval-run
  artifacts and is gitignored.

## How v3 evolves v1 and v2

All three systems share the same two responsibilities — **shape the prompt**
and **generate a ParaView script** — and the same lineage: the same
angle-bracket sentinel convention, the same five canonical scenarios and
datasets, and the same "extract the first python block" output contract.

- **v1** is a monolithic Python orchestrator (`chatvis/main.py`, `chatvis/llm.py`):
  LLM prompt-improvement → code generation → execute under `pvpython` → a
  bounded repair loop, with ParaView snippets inlined as few-shot context.
- **v2** keeps that orchestrator but replaces prompt-improvement with FAISS
  retrieval, injecting retrieved snippets into the code-generation prompt.
- **v3** decomposes the same two responsibilities into independent, reusable
  OpenCode primitives. The **subagent** owns prompt-shaping (an evolution of
  v1's prompt-improvement stage, now interactive and path-blocking). The
  **skill** owns code generation, backed by a curated, load-on-demand reference
  corpus (an evolution of v1's inline snippets and v2's retrieved snippets) plus
  an explicit "gotchas" layer. The repair loop is delegated to the host agent
  rather than being a hardcoded bounded loop.

| Stage               | v1                                | v2                                | v3                                                 |
| ------------------- | --------------------------------- | --------------------------------- | -------------------------------------------------- |
| Prompt shaping      | LLM prompt-improvement (few-shot) | (dropped — replaced by retrieval) | `paraview-prompt-formatter` subagent (interactive) |
| Context for codegen | Inline few-shot snippets          | FAISS-retrieved snippets          | Load-on-demand `references/` catalogs + gotchas    |
| Code generation     | `generate_code_v1`                | `generate_code_v2`                | `paraview-coder` skill                             |
| Execution + repair  | `pvpython` + bounded repair loop  | `pvpython` + bounded repair loop  | delegated to the host agent                        |
| Packaging           | Python pipeline (CLI `v1`)        | Python pipeline (CLI `v2`)        | OpenCode subagent + skill (not wired into the CLI) |

## Status and usage

v3 is an experiment. It is **not** installed by `uv sync` and has no entry point
in the package. To use the components, register them with OpenCode (for example,
by linking the agent and skill into an OpenCode agents/skills directory); the
package CLI is unaffected either way. Treat `v1`/`v2` as the wired pipelines and
`v3` as the direction-of-travel prototype.
