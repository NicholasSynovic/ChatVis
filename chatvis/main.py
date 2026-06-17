"""ChatVis CLI entry point and end-to-end pipeline orchestrator.

The CLI is subcommand-based (see :mod:`chatvis.cli`). :func:`main`
dispatches on the chosen subcommand:

* ``v1`` --- the wired single-scenario pipeline, executed by
  :func:`run_v1_pipeline`.
* ``v2`` --- the RAG-based pipeline, executed by
  :func:`run_v2_pipeline`.

The v1 pipeline wires four stages together:

1. :func:`chatvis.llm.improve_prompt_v1` rewrites a stock scenario
   description as an LLM-improved prompt.
2. :func:`chatvis.llm.generate_code_v1` asks the LLM for a ParaView
   script implementing the improved prompt.
3. :func:`chatvis.script.first_python_block` +
   :func:`chatvis.script.write_script` extract and persist the
   script.
4. :func:`chatvis.pvpython.run_pvpython` executes the script.

The v2 pipeline replaces stage 1 with FAISS retrieval:

1. The scenario description is used to query a FAISS index of ParaView
   code snippets (built on demand via
   :class:`chatvis.v2.documents.code.CodeEmbeddings`).
2. :func:`chatvis.llm.generate_code_v2` asks the LLM for a ParaView
   script, injecting the retrieved snippets into the user prompt.
3. Extraction / persistence (shared with v1).
4. :func:`chatvis.pvpython.run_pvpython` executes the script.

If pvpython produces a traceback, :func:`chatvis.llm.improve_code_v1`
(v1) or :func:`chatvis.llm.improve_code_v2` (v2) is called in a
bounded repair loop driven by ``--max-repair-attempts``.

Exit codes:

* ``0`` --- script executed cleanly (no extracted tracebacks).
* ``1`` --- repair loop exhausted without producing a clean run.
* ``2`` --- pre-flight configuration error (missing data file,
  missing or non-executable pvpython, missing RAG dependency).
"""

import logging
import sys
from argparse import Namespace
from logging import Logger
from pathlib import Path

from chatvis.cli import CLI
from chatvis.llm import (
    OpenAIModel,
    generate_code_v1,
    generate_code_v2,
    improve_code_v1,
    improve_code_v2,
    improve_prompt_v1,
)
from chatvis.logger import configure_logging
from chatvis.pvpython import run_pvpython
from chatvis.script import derive_script_path, first_python_block, write_script
from chatvis.utils import extract_error_messages

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


def run_v1_pipeline(cli_args: Namespace, logger: Logger) -> int:
    """Execute the full v1 pipeline. Returns the process exit code."""
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
        argo=cli_args.argo_shim,
        logger=logger,
    )

    # ----- Stage 1: prompt improvement -----
    logger.info("[1/4] Improving scenario prompt via LLM...")
    improved_prompt: str = improve_prompt_v1(
        model=model,
        scenario=cli_args.scenario,
        input_path=cli_args.data_filepath,
        output_path=cli_args.screenshot_path,
    )
    logger.debug("Improved prompt:\n%s", improved_prompt)

    # ----- Stage 2: code generation -----
    logger.info("[2/4] Generating ParaView script via LLM...")
    llm_response: str = generate_code_v1(
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
        repair_response: str = improve_code_v1(
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


def _build_v2_query(
    scenario: str,
    input_path: Path,
    output_path: Path,
) -> str:
    """Build the v2 retrieval/generation query from the scenario prompt.

    Reuses the same user-facing scenario descriptions as v1
    (:class:`chatvis.v1.prompts.user_prompts.UserPrompts`), so the two
    pipelines start from an identical task statement; only the way that
    statement is turned into a script differs.
    """
    from chatvis.v1.prompts.user_prompts import UserPrompts

    scenario_key: str = scenario.replace("-", "_").upper()
    return UserPrompts[scenario_key].format(
        input_path=input_path,
        output_path=output_path,
    )


def _retrieve_snippets(cli_args: Namespace, query: str, logger: Logger) -> str:
    """Retrieve ParaView example snippets for ``query`` via FAISS.

    The FAISS index and metadata lookup are loaded from the configured
    paths when present; otherwise they are built on demand (which, on a
    cold cache, downloads the sentence-transformers embedding model and
    embeds every bundled snippet -- this can be slow on the first run).

    Returns the retrieved snippets serialised as a JSON array string,
    ready to drop into the ``json`` fence of the v2 user prompt.
    """
    # Imported lazily: CodeEmbeddings pulls in faiss + sentence-transformers,
    # which the v1 path never needs. Keeping the import here ensures a v1
    # run (and plain ``import chatvis.main``) does not pay that cost.
    from chatvis.v2.documents.code import CodeEmbeddings

    embeddings: CodeEmbeddings = CodeEmbeddings(
        faiss_index_path=cli_args.faiss_index,
        metadata_lookup_path=cli_args.metadata_lookup,
        top_k_results=cli_args.top_k,
    )

    if not cli_args.faiss_index.exists() or not cli_args.metadata_lookup.exists():
        logger.warning(
            "FAISS index (%s) or metadata lookup (%s) not found; building "
            "now. The first build downloads the embedding model and may "
            "take a while.",
            cli_args.faiss_index,
            cli_args.metadata_lookup,
        )
        embeddings.embed_documents()

    snippets: list[str] = embeddings.query(text=query)
    logger.info("Retrieved %d snippet(s) from FAISS index", len(snippets))
    # Each snippet is already a JSON object string; assemble them into a
    # single valid JSON array for the user prompt's ``json`` fence.
    return "[\n" + ",\n".join(snippets) + "\n]"


def run_v2_pipeline(cli_args: Namespace, logger: Logger) -> int:
    """Execute the full v2 (RAG) pipeline. Returns the process exit code."""
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
    logger.info("FAISS index: %s", cli_args.faiss_index)
    logger.info("Metadata lookup: %s", cli_args.metadata_lookup)
    logger.info("Top-k snippets: %s", cli_args.top_k)
    logger.info("Max repair attempts: %s", cli_args.max_repair_attempts)

    # ----- Build LLM client -----
    model: OpenAIModel = OpenAIModel(
        api_key=cli_args.username,
        model_name=cli_args.model,
        endpoint=cli_args.endpoint,
        argo=cli_args.argo_shim,
        logger=logger,
    )

    # ----- Stage 1: RAG retrieval -----
    logger.info("[1/3] Retrieving ParaView snippets via FAISS...")
    query: str = _build_v2_query(
        scenario=cli_args.scenario,
        input_path=cli_args.data_filepath,
        output_path=cli_args.screenshot_path,
    )
    try:
        code_snippets: str = _retrieve_snippets(
            cli_args=cli_args,
            query=query,
            logger=logger,
        )
    except ImportError as exc:
        logger.error(
            "v2 requires the RAG dependencies (faiss-cpu, sentence-transformers): %s",
            exc,
        )
        return _EXIT_CONFIG_ERROR
    logger.debug("Retrieved snippets:\n%s", code_snippets)

    # ----- Stage 2: code generation -----
    logger.info("[2/3] Generating ParaView script via LLM...")
    llm_response: str = generate_code_v2(
        model=model,
        prompt=query,
        code_snippets=code_snippets,
    )
    logger.debug("Raw LLM response (code-gen):\n%s", llm_response)

    # ----- Extract + persist -----
    logger.info("Extracting and writing script to %s", script_path)
    try:
        script_source: str = first_python_block(llm_response)
    except ValueError as exc:
        logger.error("Code-gen response had no python block: %s", exc)
        return _EXIT_REPAIR_EXHAUSTED
    write_script(code=script_source, script_path=script_path)

    # ----- Stage 3: execute, repair if needed -----
    logger.info("[3/3] Executing script under pvpython...")
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
        repair_response: str = improve_code_v2(
            model=model,
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


# Back-compat alias. ``run_pipeline`` was the single-pipeline entry
# point before the CLI gained ``v1`` / ``v2`` subcommands; keep the
# name available so any out-of-tree caller does not break.
run_pipeline = run_v1_pipeline


def main() -> None:
    cli_args: Namespace = CLI().parser()

    logger: Logger = setup_logger(
        log_to_file=cli_args.log_file,
        log_level=cli_args.log_level,
    )

    logger.debug("Command line args: %s", cli_args.__dict__)

    exit_code: int
    if cli_args.subcommand == "v1":
        exit_code = run_v1_pipeline(cli_args=cli_args, logger=logger)
    elif cli_args.subcommand == "v2":
        exit_code = run_v2_pipeline(cli_args=cli_args, logger=logger)
    else:
        # Defensive: argparse already requires a known subcommand, but
        # guard so a future subparser addition cannot silently fall
        # through to a NameError or AttributeError.
        logger.error("Unknown subcommand: %r", cli_args.subcommand)
        exit_code = _EXIT_CONFIG_ERROR

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
