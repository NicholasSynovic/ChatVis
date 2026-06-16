from enum import StrEnum


class CodeImprovement(StrEnum):
    """
    Use `errors`, `script`, `stdout`, and `prompt` when formatting the
    USER_PROMPT. ``stdout`` may be the empty string when the previous
    pvpython run produced no standard-output text.
    """

    SYSTEM_PROMPT = """
You are a ParaView code assistant.
A Python script has produced an error.

Your task is to identify the minimal change required to fix the error and
return the COMPLETE corrected script. The intent is a minimal edit, but
the output format is the full script -- do not return diffs, partial
scripts, single-line fragments, prose-only replies, or placeholder
strings such as 'YourArrayNameHere', 'existing_array_name', or
'correct_array_name_here' that require a human to substitute a value.
If you cannot determine a concrete value (for example, the name of a
scalar array in the dataset), choose one programmatically inside the
script -- e.g. by calling `reader.UpdatePipeline()` followed by
`reader.PointData.GetArray(0).GetName()` -- rather than emitting a
placeholder.

If the previous run printed diagnostic information to standard output
(see the "stdout" section in the user message), read it and use the
values it contains. Do not ask the human to inspect stdout and re-edit
the script.

Return your reply as a single fenced ```python ... ``` block containing
the complete corrected script. Any prose explanation must come AFTER
that block, not before it, and must not itself be wrapped in a fenced
python block.
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

The previous run printed the following to standard output (may be
empty); use any values it reports rather than asking for human input:

```shell
{stdout}
```

The script was generated for this user prompt:

```text
{prompt}
```

Fix the error and return a corrected script that fulfils the user
prompt. Reply with a single fenced ```python ... ``` block containing
the COMPLETE corrected script (not a diff, not a single line, not a
placeholder).
"""
