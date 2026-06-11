"""Agentic ParaView code generation + self-repair loop.

This module ports the agentic structure from the working scenario notebooks
(see ``notebooks/ml-dvr.ipynb``, ``notebooks/ml-iso.ipynb``, and the live
``while errors:`` loops in ``notebooks/stream-glyph.ipynb`` and
``notebooks/points-surf-clip.ipynb``).

The loop:

    1. Generate a refined natural-language prompt from the scenario template.
    2. Generate ParaView Python code from that prompt.
    3. Persist the first ``python`` code block from the LLM response to disk.
    4. Execute it via ``pvpython`` as a subprocess.
    5. If the stderr contains a Python traceback, ask the LLM to repair the
       script and try again, up to ``max_iterations`` times.
"""

import subprocess
from pathlib import Path

from pydantic import BaseModel

from chatvis.documents.code_generation import CODE_GENERATION_PROMPTS
from chatvis.documents.prompt_generation import PROMPT_GENERATION_PROMPTS
from chatvis.llm import (
    OpenAIModel,
    code_generation,
    code_improvement,
    parse_response,
    prompt_generation,
)
from chatvis.utils import extract_error_messages, extract_python_code


class AgentResult(BaseModel):
    """Structured outcome of an agent run."""

    scenario: str
    script: str
    script_path: Path
    iterations: int
    success: bool
    error_history: list[list[str]]


def _write_script(
    code: str,
    work_dir: Path,
    scenario: str,
    attempt: int,
) -> Path:
    """Persist a generated script to ``<work_dir>/<scenario>_<attempt>.py``."""
    path: Path = work_dir / f"{scenario}_{attempt}.py"
    path.write_text(code)
    return path


def _run_pvpython(script_path: Path) -> list[str]:
    """Invoke ``pvpython <script_path>`` and return any tracebacks in stderr."""
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["pvpython", str(script_path)],
        capture_output=True,
        text=True,
    )
    return extract_error_messages(result.stderr)


def _first_code_block(response_text: str) -> str:
    """Return the first ``python`` code block from an LLM response."""
    blocks: list[str] = extract_python_code(response_text)
    if not blocks:
        raise ValueError("LLM response contained no ```python``` block")
    return blocks[0]


def run_agent(
    scenario: str,
    input_path: Path,
    output_path: Path,
    work_dir: Path,
    generator_model: OpenAIModel,
    repair_model: OpenAIModel | None = None,
    max_iterations: int = 5,
) -> AgentResult:
    """Drive the prompt -> code -> execute -> repair loop for a scenario.

    Args:
        scenario: scenario key (must exist in both ``PROMPT_GENERATION_PROMPTS``
            and ``CODE_GENERATION_PROMPTS``).
        input_path: dataset path to substitute into the scenario prompt.
        output_path: screenshot output path to substitute into the prompt.
        work_dir: directory into which each generated script is written.
        generator_model: model used for the initial prompt + code generation.
        repair_model: model used inside the repair loop. Defaults to
            ``generator_model`` if omitted (matches notebook behavior when no
            second model is needed).
        max_iterations: maximum repair attempts after the initial generation.
            ``0`` disables repair entirely.

    Returns:
        AgentResult capturing the final script, where it lives on disk, the
        number of repair iterations consumed, whether the final run was
        error-free, and the per-iteration error history (index 0 is the
        initial run, subsequent indices are post-repair runs).
    """
    if scenario not in CODE_GENERATION_PROMPTS:
        raise KeyError(f"scenario {scenario!r} missing from CODE_GENERATION_PROMPTS")
    if scenario not in PROMPT_GENERATION_PROMPTS:
        raise KeyError(f"scenario {scenario!r} missing from PROMPT_GENERATION_PROMPTS")

    repair_model = repair_model or generator_model
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate refined natural-language prompt.
    generated_prompt: str = parse_response(
        prompt_generation(
            pgp=PROMPT_GENERATION_PROMPTS[scenario],
            openai=generator_model,
            input_path=input_path,
            output_path=output_path,
        )
    )

    # 2. Generate initial ParaView script.
    script_text: str = parse_response(
        code_generation(
            generated_prompt=generated_prompt,
            cgp=CODE_GENERATION_PROMPTS[scenario],
            openai=generator_model,
        )
    )
    code: str = _first_code_block(script_text)
    script_path: Path = _write_script(code, work_dir, scenario, 0)

    # 3. Execute the initial script.
    errors: list[str] = _run_pvpython(script_path)
    error_history: list[list[str]] = [errors]

    # 4. Repair loop.
    iteration: int = 0
    while errors and iteration < max_iterations:
        iteration += 1

        repaired_text: str = parse_response(
            code_improvement(
                generated_prompt=generated_prompt,
                generated_code=code,
                shell_errors="\n".join(errors),
                openai=repair_model,
            )
        )
        code = _first_code_block(repaired_text)
        script_path = _write_script(code, work_dir, scenario, iteration)

        errors = _run_pvpython(script_path)
        error_history.append(errors)

    return AgentResult(
        scenario=scenario,
        script=code,
        script_path=script_path,
        iterations=iteration,
        success=not errors,
        error_history=error_history,
    )
