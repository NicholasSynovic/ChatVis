import re

import pandas as pd


def pydantic_to_dataframe(models: list) -> pd.DataFrame:
    """Converts a list of Pydantic models into a pandas DataFrame."""
    return pd.DataFrame([model.model_dump() for model in models])


def extract_python_code(text: str) -> list[str]:
    """
    Extract Python code from encapsulated Markdown flavored code blocks.

    Returns a list of strings of each code block.
    """
    # Store individual code blocks to
    code_blocks: list[str] = []

    # Regular expression to find all occurrences of Python code blocks
    code_blocks = re.findall(r"```python(.*?)```", text, re.DOTALL)

    # Iterate through code blocks and format them
    code_block: str
    for code_block in code_blocks:
        # Strip leading/trailing whitespace and maintain internal formatting
        formatted_code = code_block.strip()
        code_blocks.append(formatted_code)

    return code_blocks


def extract_error_messages(stderr_output: str):
    """
    Extract stderr text focussing on tracebacks and exceptions.

    Returns a list of strings of the error messages
    """
    # Split the stderr output into lines
    error_messages: list[str] = stderr_output.strip().split("\n")
    return error_messages
