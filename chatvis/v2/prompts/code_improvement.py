from enum import StrEnum


class CodeImprovement(StrEnum):
    """
    Use `errors`, `script`, and `stdout`, when formatting the USER_PROMPT.
    ``stdout`` may be the empty string when the previous pvpython run produced
    no standard-output text. Use the system prompt from
    `code_generation.CodeGeneration` with the RAG completions for the code
    improvement system prompt
    """

    USER_PROMPT = """
I tried running the following Python script and encountered an error.

**Error Message:**
{errors}

**Original Script:**
{script}

**Standard Output:**
{stdout}

Can you help me fix the issue and provide a corrected version of the script?
Please make sure the new script runs correctly without errors.
"""
