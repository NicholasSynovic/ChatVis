from enum import StrEnum


class CodeImprovement(StrEnum):
    """
    Use `errors`, `script`, and `prompt` when formatting the USER_PROMPT.
    """

    SYSTEM_PROMPT = """
You are a ParaView code assistant.
A Python script has produced an error.
Focus on the error line and fix only what is necessary, do not rewrite the entire script.
"""

    USER_PROMPT = """
I encountered the following Python error:

```shell
{errors}
```

Here is the script that produced the error:

```python
{script}
```

The script was generated for this user prompt:

```text
{prompt}
```

Fix the error and return a corrected script that fulfils the user prompt.
"""
