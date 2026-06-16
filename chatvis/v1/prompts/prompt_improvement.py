from enum import StrEnum


class PromptImprovement(StrEnum):
    """
    Use `user_input` and `example_user_in|output` when formatting the USER_PROMPT.
    """

    SYSTEM_PROMPT = (
        "You are a prompt generator. Do not provide any other text than the prompt. "
        "Preserve every concrete value from the user input verbatim in the improved "
        "prompt: file paths, file names, numeric values (including isosurface "
        "values, thresholds, coordinates, image dimensions), variable and array "
        "names, axis directions, and color names. Do not drop, summarize, "
        "paraphrase, or substitute any of these values. If the user input says "
        '"isosurface of var0 at value 0.5", the improved prompt must also say '
        '"at value 0.5".'
    )

    USER_PROMPT = """
Generate the most effective prompt for the user input:

```user input
{user_input}
```

Here is an example of a user input:

```example user input
{example_user_input}
```

Here is an example of a prompt generated from the example user input:

```example user output
{example_user_output}
```
"""
