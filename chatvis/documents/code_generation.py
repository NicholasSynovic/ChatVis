from string import Template

from pydantic import BaseModel

from chatvis.documents.code_examples import CODE_EXAMPLES, CodeExample

_PROLOGUE: str = """
    You are a code assistant.
    Please read the user prompt line by line and process it step by step.
"""

_TOP_LEVEL_OPERATIONS: str = f"""
    Some operations are provided as examples:

    ```python
    {CODE_EXAMPLES["code_to_read"]}
    ```

    ```python
    {CODE_EXAMPLES["code_to_slice"]}
    ```

    ```python
    {CODE_EXAMPLES["code_to_contour"]}
    ```

    ```python
    {CODE_EXAMPLES["code_to_clip"]}
    ```
    """

_RENDER_OPERATIONS: str = f"""
    Use the following examples and change the render view as the user is specifying:

    ```python
    {CODE_EXAMPLES["code_to_render_view"]}
    ```

    ```python
    {CODE_EXAMPLES["code_to_render_view_direction"]}
    ```

    ```python
    {CODE_EXAMPLES["code_to_isometric_view"]}
    ```

    ```python
    {CODE_EXAMPLES["code_to_contour1Display"]}
    ```
"""

_EPILOG_OPERATIONS: str = f"""
    Please use the example to write the correct code for the user.
    Please use this code in all generated code snippets:

    ```python
    {CODE_EXAMPLES["code_to_create_layout"]}
    ```

    Do not use `clip1.InsideOut`.
    Save the screenshot using:

    ```python
    {CODE_EXAMPLES["code_to_save"]}
    ```
"""


class CodeGenerationPrompt(BaseModel):
    system_prompt: str
    user_prompt: str = ""


CODE_GENERATION_PROMPTS: dict[str, CodeGenerationPrompt] = {
    "ml-dvr": CodeGenerationPrompt(
        system_prompt=f"""
{_PROLOGUE}

{_TOP_LEVEL_OPERATIONS}

Use the following functions:

```python
{CODE_EXAMPLES["code_to_opacity_transfer_function"]}
```

```python
{CODE_EXAMPLES["code_to_color_transfer_function"]}
```

{_RENDER_OPERATIONS}

{_EPILOG_OPERATIONS}
"""
    ),
    "ml-iso": CodeGenerationPrompt(
        system_prompt=f"""
{_PROLOGUE}

{_TOP_LEVEL_OPERATIONS}

{_RENDER_OPERATIONS}

{_EPILOG_OPERATIONS}
"""
    ),
    "ml-slice-iso": CodeGenerationPrompt(
        system_prompt=f"""
{_PROLOGUE}

{_TOP_LEVEL_OPERATIONS}

{_RENDER_OPERATIONS}

{_EPILOG_OPERATIONS}
"""
    ),
    "points-surf-clip": CodeGenerationPrompt(
        system_prompt=f"""
{_PROLOGUE}

{_TOP_LEVEL_OPERATIONS}

{_RENDER_OPERATIONS}

{_EPILOG_OPERATIONS}
"""
    ),
    "stream-glyph": CodeGenerationPrompt(
        system_prompt=f"""
{_PROLOGUE}

{_TOP_LEVEL_OPERATIONS}

```python
{CODE_EXAMPLES["code_to_tube"]}
```

```python
 {CODE_EXAMPLES["code_to_glyph"]}
```

```python
{CODE_EXAMPLES["code_to_stream_tacer"]}
```

{_RENDER_OPERATIONS}

```python
{CODE_EXAMPLES["code_to_color_tube_glyphs_Temp_variable"]}
```

{_EPILOG_OPERATIONS}
"""
    ),
}
