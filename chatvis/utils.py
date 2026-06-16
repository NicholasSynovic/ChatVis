import re

# VTK / ParaView log substrings that indicate a silent pipeline failure:
# pvpython exits 0 with no Python traceback, but the rendered output is
# empty geometry. Treating these as errors lets the repair loop retry
# instead of accepting a blank screenshot.
#
# Patterns are matched case-sensitively against each stderr line after
# stripping the surrounding ANSI escapes. Keep the list narrow -- false
# positives waste an LLM round-trip and may overwrite a usable script.
_SILENT_FAILURE_PATTERNS: tuple[str, ...] = (
    "Contour array is null",
    "Error reading binary data",
    "Unable to update",
    "Update failed",
    "no input",
    "Cannot show the data",
)

# Strip CSI escape sequences (colour codes) so pattern matching above
# does not need to anticipate them.
_ANSI_RE: re.Pattern[str] = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def extract_python_code(text: str) -> list[str]:
    """
    Extract Python code from encapsulated Markdown flavored code blocks.

    Returns a list of strings of each code block.
    """
    # Regular expression to find all occurrences of Python code blocks
    raw_blocks: list[str] = re.findall(r"```python(.*?)```", text, re.DOTALL)

    # Strip leading/trailing whitespace and maintain internal formatting
    return [block.strip() for block in raw_blocks]


def extract_error_messages(stderr_output: str) -> list[str]:
    """
    Extract failure signals from a subprocess stderr stream.

    Two kinds of failures are surfaced:

    1. Python tracebacks, anchored on ``Traceback (most recent call last):``.
       Benign stderr noise (warnings, deprecation notices) does not register.
    2. Silent VTK / ParaView pipeline failures -- pvpython can exit 0 with
       no traceback and still produce an empty image (e.g. ``Contour array
       is null`` when the upstream reader returned no data). Lines matching
       one of :data:`_SILENT_FAILURE_PATTERNS` are returned verbatim so the
       repair loop can react to them.

    Returns a list of strings, one per detected failure.
    """
    lines: list[str] = stderr_output.split("\n")
    error_messages: list[str] = []

    for i, line in enumerate(lines):
        if "Traceback (most recent call last):" not in line:
            continue

        # Walk forward to the first ``File ...`` frame, then collect
        # subsequent lines until the next ``File ...`` frame or EOF.
        for j in range(i + 1, len(lines)):
            if not lines[j].strip().startswith("File"):
                continue

            error_detail: str = lines[j].strip()
            k: int = j + 1
            while k < len(lines) and not lines[k].strip().startswith("File"):
                error_detail += "\n" + lines[k].strip()
                k += 1
            error_messages.append(error_detail)
            break

    # Second pass: silent pipeline failures. Only consider these if no
    # traceback was found, so a real Python error is never masked by a
    # downstream VTK warning describing the same root cause.
    if not error_messages:
        for line in lines:
            stripped: str = _ANSI_RE.sub("", line).strip()
            if not stripped:
                continue
            if any(pattern in stripped for pattern in _SILENT_FAILURE_PATTERNS):
                error_messages.append(stripped)

    return error_messages
