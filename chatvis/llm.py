from pathlib import Path

from openai import Client
from openai.types.chat import ChatCompletion

from chatvis.documents.code_generation import CodeGenerationPrompt
from chatvis.documents.code_improvement import CodeImprovementPrompt
from chatvis.documents.prompt_generation import PromptGenerationPrompt


class OpenAIModel:
    def __init__(
        self,
        api_key: str,
        endpoint: str = "https://argo.apps.inside.anl.gov/v1",
        model_name: str = "gpt4o",
        temperature: float = 42.0,
    ) -> None:
        self.endpoint: str = endpoint
        self.temperature: float = temperature
        self.model_name: str = model_name.lower()
        self.client: Client = Client(
            base_url=self.endpoint,
            api_key=api_key,
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ChatCompletion:
        return self.client.chat.completions.create(
            model=self.model_name,
            temperature=self.temperature,
            n=1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )


def prompt_generation(
    pgp: PromptGenerationPrompt,
    openai: OpenAIModel,
    input_path: Path,
    output_path: Path,
) -> ChatCompletion:
    user_prompt: str = pgp.user_prompt.substitute(
        input_path=input_path,
        output_path=output_path,
        input_prompt=pgp.example_prompt.input_prompt,
        generated_prompt=pgp.example_prompt.generated_prompt,
    )

    return openai.chat(system_prompt=pgp.system_prompt, user_prompt=user_prompt)


def code_generation(
    generated_prompt: str,
    cgp: CodeGenerationPrompt,
    openai: OpenAIModel,
) -> ChatCompletion:
    return openai.chat(
        system_prompt=cgp.system_prompt,
        user_prompt=generated_prompt,
    )


def code_improvement(
    generated_prompt: str,
    generated_code: str,
    shell_errors: str,
    openai: OpenAIModel,
) -> ChatCompletion:
    cip: CodeImprovementPrompt = CodeImprovementPrompt()
    user_prompt: str = cip.user_prompt.substitute(
        errors=shell_errors,
        python_script=generated_code,
        prompt=generated_prompt,
    )

    return openai.chat(system_prompt=cip.system_prompt, user_prompt=user_prompt)


def parse_response(response: ChatCompletion) -> str:
    content: str | None = response.choices[0].message.content

    if content is None:
        content = ""

    return content
