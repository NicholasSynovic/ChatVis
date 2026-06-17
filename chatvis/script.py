"""Generated-script persistence helpers.

Bridges the LLM stage (raw Markdown reply containing one or more
``python`` fenced blocks) and the execution stage (a ``.py`` file on
disk ready for ``pvpython``). Stays free of subprocess and OpenAI
imports so it can be exercised without either dependency.
"""

import logging
from logging import Logger
from pathlib import Path

from chatvis.utils import extract_python_code

logger: Logger = logging.getLogger(__name__)


def derive_script_path(screenshot_path: Path) -> Path:
    """Return the ``.py`` script path that sits beside ``screenshot_path``.

    The pipeline writes the generated ParaView script next to its
    output screenshot, sharing the stem and parent directory:

        ``/out/foo.png`` -> ``/out/foo.py``

    The returned path is not created on disk.
    """
    return screenshot_path.with_suffix(".py")


def first_python_block(llm_response: str) -> str:
    """Return the first ``python`` fenced code block from ``llm_response``.

    The LLM is expected to wrap the generated ParaView script in a
    Markdown ``` ```python ... ``` ``` fence. When several blocks are
    present (e.g. helper snippets followed by the main script) we keep
    only the first, matching the behavior baked into every notebook in
    ``notebooks/``.

    Raises:
        ValueError: when the response contains no ``python`` fenced
            block. Surfacing this early prevents writing an empty file
            and prevents ``pvpython`` from being invoked against
            nonsense.
    """
    blocks: list[str] = extract_python_code(llm_response)
    if not blocks:
        raise ValueError(
            "LLM response did not contain a ```python``` fenced code block"
        )
    if len(blocks) > 1:
        logger.debug(
            "LLM response contained %d python blocks; keeping the first",
            len(blocks),
        )
    return blocks[0]


def write_script(code: str, script_path: Path) -> Path:
    """Write ``code`` to ``script_path``, creating parent dirs as needed.

    Returns the path that was written, so callers can chain the result
    into ``run_pvpython`` without re-deriving it.
    """
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(code, encoding="utf-8")
    logger.debug("Wrote %d bytes to %s", len(code), script_path)
    return script_path
