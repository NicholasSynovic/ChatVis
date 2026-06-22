# TODO

Deferred / skipped steps from the `paraview-coder` skill creation
(`chatvis/v3/skills/paraview-coder/`). These were intentionally postponed —
capture them here so they are not lost.

## paraview-coder skill — deferred work

- [ ] **Description-optimization loop.** Tune the SKILL.md `description` field for
      reliable triggering. Run the skill-creator optimizer:
      `python -m scripts.run_loop --eval-set <trigger-evals.json> --skill-path
chatvis/v3/skills/paraview-coder --model <model-id> --max-iterations 5 --verbose`
      (from the skill-creator dir). Requires the `claude` CLI. First generate
      ~20 should-trigger / should-not-trigger queries and review them.

- [ ] **pvpython execution + repair-loop content.** The skill deliberately stops
      at script _generation_. A future revision (or a sibling skill) should add
      the run-and-repair workflow: run the script under pvpython, parse the
      traceback / silent-failure signals (cf. `chatvis/utils.py`
      `extract_error_messages`), and iterate. Keep generation and execution as
      separable concerns.

- [ ] **Live pvpython verification of generated scripts.** The eval loop only
      checked the generated scripts statically (string/regex assertions); none
      were executed. Run the three iteration-1 scripts under a real `pvpython`
      (ParaView 5.12+; see `environment.yaml`) and visually compare the
      screenshots against `data/benchmark/<scenario>/`.

- [ ] **Replace the non-discriminating eval.** `isosurface-named-array` passed
      7/7 for both with-skill and baseline — it does not exercise the skill's
      value. Swap in a volume-rendering case to stress the atomic
      transfer-function gotcha (the most failure-prone path).

- [ ] **Capture timing/token data.** The iteration-1 subagent runs did not
      surface `total_tokens` / `duration_ms`; `timing.json` files are zeroed.
      Capture real numbers on the next run for a meaningful time/token delta.

- [ ] **Package the skill.** When a packaging tool is available, run
      `python -m scripts.package_skill chatvis/v3/skills/paraview-coder` to
      produce a distributable `.skill` file.

- [ ] **Validate with the official tool.** `skills-ref` was not installed in this
      session (validation was done manually). Install it and run
      `skills-ref validate chatvis/v3/skills/paraview-coder` to confirm.
