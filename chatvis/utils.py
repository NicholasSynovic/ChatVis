import re


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
    Extract Python tracebacks from a subprocess stderr stream.

    Only content anchored on ``Traceback (most recent call last):`` is
    returned, so benign stderr noise (warnings, deprecation notices) does
    not register as an error.

    Returns a list of strings, one per detected traceback.
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

    return error_messages
