"""ChatVis CLI entry point and end-to-end pipeline orchestrator.

Wires the four pipeline stages together:

1. :func:`chatvis.llm.improve_prompt` rewrites a stock scenario
   description as an LLM-improved prompt.
2. :func:`chatvis.llm.generate_code` asks the LLM for a ParaView
   script implementing the improved prompt.
3. :func:`chatvis.v1.script.first_python_block` +
   :func:`chatvis.v1.script.write_script` extract and persist the
   script.
4. :func:`chatvis.v1.pvpython.run_pvpython` executes the script.

If pvpython produces a traceback, :func:`chatvis.llm.improve_code`
is called in a bounded repair loop driven by
``--max-repair-attempts``.

Exit codes:

* ``0`` --- script executed cleanly (no extracted tracebacks).
* ``1`` --- repair loop exhausted without producing a clean run.
* ``2`` --- pre-flight configuration error (missing data file,
  missing or non-executable pvpython, unknown scenario).
"""

import logging
import sys
from argparse import Namespace
from logging import Logger
from pathlib import Path

from chatvis.cli import CLI
from chatvis.llm import OpenAIModel, generate_code, improve_code, improve_prompt
from chatvis.logger import configure_logging
from chatvis.utils import extract_error_messages
from chatvis.v1.pvpython import run_pvpython
from chatvis.v1.script import derive_script_path, first_python_block, write_script

# Scenario -> expected dataset basename. Mismatches log a warning but
# do not abort: the LLM never inspects the file, so a user running an
# experiment with a swapped dataset should still be able to proceed.
_EXPECTED_DATA_BY_SCENARIO: dict[str, str] = {
    "ml-dvr": "ml-100.vtk",
    "ml-iso": "ml-100.vtk",
    "ml-slice-iso": "ml-100.vtk",
    "points-surf-clip": "can_points.ex2",
    "stream-glyph": "disk.ex2",
}

# Exit codes.
_EXIT_OK: int = 0
_EXIT_REPAIR_EXHAUSTED: int = 1
_EXIT_CONFIG_ERROR: int = 2


def setup_logger(log_to_file: bool, log_level: str) -> Logger:
    log_path: Path | None = configure_logging(
        log_to_file=log_to_file,
        level=logging.getLevelNamesMapping()[log_level.upper()],
    )

    logger: Logger = logging.getLogger("chatvis")

    if log_path is not None:
        logger.info("Logging to %s", log_path)

    return logger


def check_data(
    scenario: str,
    data_filepath: Path,
    logger: Logger,
) -> None:
    """Validate ``--data-filepath`` and warn on scenario mismatch.

    Existence is enforced (raises ``FileNotFoundError`` so the caller
    can exit ``_EXIT_CONFIG_ERROR``). Basename mismatch against
    :data:`_EXPECTED_DATA_BY_SCENARIO` is a warning only, since the
    LLM and pvpython will both happily accept any path the caller
    provides.
    """
    if not data_filepath.exists():
        raise FileNotFoundError(f"--data-filepath does not exist: {data_filepath}")

    expected: str | None = _EXPECTED_DATA_BY_SCENARIO.get(scenario)
    if expected is not None and data_filepath.name != expected:
        logger.warning(
            "Scenario %r is normally run with %r, got %r. Proceeding anyway.",
            scenario,
            expected,
            data_filepath.name,
        )


def _run_and_extract_errors(
    pvpython_path: Path | None,
    script_path: Path,
    logger: Logger,
) -> tuple[list[str], str]:
    """Execute ``script_path`` and return any extracted tracebacks plus stdout.

    The stdout text is propagated back so the orchestrator can feed it
    into the next repair-iteration prompt; the LLM sometimes asks the
    script to ``print(...)`` diagnostic information (e.g. available
    PointData array names) and previously had no way to see what its
    own previous attempt printed.
    """
    returncode, stdout, stderr = run_pvpython(
        pvpython_path=pvpython_path,
        script_path=script_path,
    )
    logger.info("pvpython exited with code %s", returncode)
    if stdout:
        logger.debug("pvpython stdout:\n%s", stdout)
    if stderr:
        logger.debug("pvpython stderr:\n%s", stderr)
    return extract_error_messages(stderr), stdout


def run_pipeline(cli_args: Namespace, logger: Logger) -> int:
    """Execute the full pipeline. Returns the process exit code."""
    # ----- Pre-flight -----
    try:
        check_data(
            scenario=cli_args.scenario,
            data_filepath=cli_args.data_filepath,
            logger=logger,
        )
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return _EXIT_CONFIG_ERROR

    script_path: Path = derive_script_path(cli_args.screenshot_path)
    logger.info("Scenario: %s", cli_args.scenario)
    logger.info("Data file: %s", cli_args.data_filepath)
    logger.info("Screenshot path: %s", cli_args.screenshot_path)
    logger.info("Script path: %s", script_path)
    logger.info("Max repair attempts: %s", cli_args.max_repair_attempts)

    # ----- Build LLM client -----
    model: OpenAIModel = OpenAIModel(
        api_key=cli_args.username,
        model_name=cli_args.model,
        endpoint=cli_args.endpoint,
        logger=logger,
    )

    # ----- Stage 1: prompt improvement -----
    logger.info("[1/4] Improving scenario prompt via LLM...")
    improved_prompt: str = improve_prompt(
        model=model,
        scenario=cli_args.scenario,
        input_path=cli_args.data_filepath,
        output_path=cli_args.screenshot_path,
    )
    logger.debug("Improved prompt:\n%s", improved_prompt)

    # ----- Stage 2: code generation -----
    logger.info("[2/4] Generating ParaView script via LLM...")
    llm_response: str = generate_code(
        model=model,
        improved_prompt=improved_prompt,
    )
    logger.debug("Raw LLM response (code-gen):\n%s", llm_response)

    # ----- Stage 3: extract + persist -----
    logger.info("[3/4] Extracting and writing script to %s", script_path)
    try:
        script_source: str = first_python_block(llm_response)
    except ValueError as exc:
        logger.error("Code-gen response had no python block: %s", exc)
        return _EXIT_REPAIR_EXHAUSTED
    write_script(code=script_source, script_path=script_path)

    # ----- Stage 4: execute, repair if needed -----
    logger.info("[4/4] Executing script under pvpython...")
    try:
        errors, stdout = _run_and_extract_errors(
            pvpython_path=cli_args.pvpython,
            script_path=script_path,
            logger=logger,
        )
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        logger.error("pvpython invocation failed pre-flight: %s", exc)
        return _EXIT_CONFIG_ERROR

    if not errors:
        logger.info("Script executed cleanly on first attempt.")
        return _EXIT_OK

    # Repair loop. The budget counts repair calls only; the initial
    # generation above is "attempt 0" and not subtracted from it.
    for attempt in range(1, cli_args.max_repair_attempts + 1):
        logger.info(
            "Detected %d traceback(s); repair attempt %d/%d...",
            len(errors),
            attempt,
            cli_args.max_repair_attempts,
        )
        # Re-read the on-disk script so the LLM sees exactly what
        # pvpython executed, not what we think we wrote.
        broken_script: str = script_path.read_text(encoding="utf-8")
        repair_response: str = improve_code(
            model=model,
            improved_prompt=improved_prompt,
            broken_script=broken_script,
            errors="\n".join(errors),
            stdout=stdout,
        )
        logger.debug(
            "Raw LLM response (repair attempt %d):\n%s",
            attempt,
            repair_response,
        )
        try:
            fixed_source: str = first_python_block(repair_response)
        except ValueError as exc:
            logger.error(
                "Repair attempt %d returned no python block: %s",
                attempt,
                exc,
            )
            return _EXIT_REPAIR_EXHAUSTED
        write_script(code=fixed_source, script_path=script_path)

        errors, stdout = _run_and_extract_errors(
            pvpython_path=cli_args.pvpython,
            script_path=script_path,
            logger=logger,
        )
        if not errors:
            logger.info(
                "Script executed cleanly after %d repair attempt(s).",
                attempt,
            )
            return _EXIT_OK

    logger.error(
        "Exhausted %d repair attempt(s); final script still produces "
        "%d traceback(s). See %s.",
        cli_args.max_repair_attempts,
        len(errors),
        script_path,
    )
    return _EXIT_REPAIR_EXHAUSTED


def main() -> None:
    cli_args: Namespace = CLI().parser()

    logger: Logger = setup_logger(
        log_to_file=cli_args.log_file,
        log_level=cli_args.log_level,
    )

    logger.debug("Command line args: %s", cli_args.__dict__)

    exit_code: int = run_pipeline(cli_args=cli_args, logger=logger)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
