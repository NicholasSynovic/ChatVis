from string import Template

from pydantic import BaseModel


class CodeImprovementPrompt(BaseModel):
    system_prompt: str = """
You are a great code assistant.
Focus on the error line.
Don't change the entire code.
"""
    user_prompt: Template = Template(
        template="""
I encountered a Python error:

```error
${errors}
```

Can you fix this Python code for the user?

```python
${python_script}
```

```prompt
{prompt}
```
"""
    )
