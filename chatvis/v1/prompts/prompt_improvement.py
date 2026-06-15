from enum import StrEnum


class PromptImprovement(StrEnum):
    """
    Use `user_input` and `example_user_in|output` when formatting the USER_PROMPT.
    """

    SYSTEM_PROMPT = (
        "You are a prompt generator. Do not provide any other text than the prompt."
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
