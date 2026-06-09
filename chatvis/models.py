from pydantic import BaseModel


class PythonCode(BaseModel):
    name: str
    code: str


class GeneratedPrompts(BaseModel):
    name: str
    input_prompt: str
    generated_prompt: str
