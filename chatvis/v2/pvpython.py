"""``pvpython`` subprocess execution helpers.

Wraps the single ``subprocess.run`` call used by the pipeline to
execute LLM-generated ParaView scripts. Kept tiny and dependency-free
so it can be exercised in isolation when iterating on the orchestrator.
"""

import logging
import os
import subprocess  # nosec B404 - executing pvpython is the entire job
from logging import Logger
from pathlib import Path

logger: Logger = logging.getLogger(__name__)


def _validate_pvpython(pvpython_path: Path | None) -> Path:
    """Return ``pvpython_path`` once it has been confirmed runnable."""
    if pvpython_path is None:
        raise ValueError(
            "pvpython path is not configured; pass --pvpython or place pvpython on PATH"
        )
    if not pvpython_path.exists():
        raise FileNotFoundError(f"pvpython not found at {pvpython_path}")
    if not os.access(pvpython_path, os.X_OK):
        raise PermissionError(f"pvpython at {pvpython_path} is not executable")
    return pvpython_path


def _validate_script(script_path: Path) -> Path:
    """Return ``script_path`` once it has been confirmed present."""
    if not script_path.exists():
        raise FileNotFoundError(f"script not found at {script_path}")
    return script_path


def run_pvpython(
    pvpython_path: Path | None,
    script_path: Path,
) -> tuple[int, str, str]:
    """Execute ``script_path`` under ``pvpython`` and capture all output.

    Args:
        pvpython_path: absolute path to the ``pvpython`` executable.
            May be ``None`` to surface a clear configuration error
            instead of an opaque ``TypeError`` from ``subprocess``.
        script_path: absolute path to the ParaView script to run.

    Returns:
        ``(returncode, stdout, stderr)``. The caller decides what
        constitutes failure; we never raise on a non-zero exit code
        because the pipeline's repair loop treats stderr tracebacks as
        the real failure signal, not the return code.

    Raises:
        ValueError, FileNotFoundError, PermissionError: when the
            configured paths are obviously unrunnable. These are
            surfaced before the subprocess is spawned.
    """
    pv: Path = _validate_pvpython(pvpython_path)
    script: Path = _validate_script(script_path)

    logger.debug("Invoking %s %s", pv, script)
    completed: subprocess.CompletedProcess[str] = subprocess.run(  # nosec B603
        [str(pv), str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    logger.debug(
        "pvpython exit=%s stdout_bytes=%s stderr_bytes=%s",
        completed.returncode,
        len(completed.stdout),
        len(completed.stderr),
    )
    return completed.returncode, completed.stdout, completed.stderr
