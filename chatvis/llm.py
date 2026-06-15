"""LLM orchestration for ChatVis.

Provides an OpenAI-compatible chat-completions wrapper configured for
deterministic, reproducible runs against Argonne's Argo endpoint, plus
the pipeline helper :func:`improve_prompt` that turns a stock scenario
description into an LLM-improved prompt suitable for code generation.
"""

import logging
from logging import Logger
from pathlib import Path

from openai import Client
from openai.types.chat import ChatCompletion

from chatvis.v1.documents.prompts import GeneratedPrompt
from chatvis.v1.prompts.prompt_improvement import PromptImprovement

# Defaults chosen for reproducibility. ``seed`` is best-effort per the
# OpenAI spec; the returned ``system_fingerprint`` lets a caller detect
# when the backend has changed in a way that may invalidate determinism.
DEFAULT_SEED: int = 42
DEFAULT_TEMPERATURE: float = 0.0
DEFAULT_TOP_P: float = 1.0
DEFAULT_N: int = 1


class OpenAIModel:
    """Thin wrapper around the OpenAI Chat Completions API.

    Argo authenticates by ANL username supplied via the OpenAI client's
    ``api_key`` parameter. The name ``api_key`` mirrors that contract.

    All sampling parameters default to deterministic values so two runs
    issued against the same backend revision should return identical
    content. Override per call only when nondeterminism is desired.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        endpoint: str,
        seed: int = DEFAULT_SEED,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        n: int = DEFAULT_N,
        logger: Logger | None = None,
    ) -> None:
        self.logger: Logger = (
            logger if logger is not None else logging.getLogger(__name__)
        )
        self.endpoint: str = endpoint
        self.model_name: str = model_name.lower()
        self.seed: int = seed
        self.temperature: float = temperature
        self.top_p: float = top_p
        self.n: int = n
        self.client: Client = Client(
            base_url=self.endpoint,
            api_key=api_key,
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        seed: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        n: int | None = None,
    ) -> ChatCompletion:
        """Issue a chat-completion request.

        Per-call overrides fall back to the instance defaults so that
        callers that want strict reproducibility do not have to thread
        the sampling parameters through every call site.
        """
        effective_seed: int = self.seed if seed is None else seed
        effective_temperature: float = (
            self.temperature if temperature is None else temperature
        )
        effective_top_p: float = self.top_p if top_p is None else top_p
        effective_n: int = self.n if n is None else n

        self.logger.debug("LLM system_prompt:\n%s", system_prompt)
        self.logger.debug("LLM user_prompt:\n%s", user_prompt)
        self.logger.debug(
            "LLM sampling params: seed=%s temperature=%s top_p=%s n=%s",
            effective_seed,
            effective_temperature,
            effective_top_p,
            effective_n,
        )

        response: ChatCompletion = self.client.chat.completions.create(
            model=self.model_name,
            seed=effective_seed,
            temperature=effective_temperature,
            top_p=effective_top_p,
            n=effective_n,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        self.logger.debug(
            "LLM system_fingerprint=%s",
            getattr(response, "system_fingerprint", None),
        )
        return response


def parse_response(response: ChatCompletion) -> str:
    """Return the first choice's content, or the empty string if absent."""
    content: str | None = response.choices[0].message.content
    return content if content is not None else ""


def _substitute_paths(text: str, input_path: Path, output_path: Path) -> str:
    """Replace the ``<input_path>`` / ``<output_path>`` sentinels.

    Few-shot example values stored in :class:`GeneratedPrompt` carry
    angle-bracket sentinels so the same enum value can be shown to the
    LLM under different concrete paths. Substitution happens here, not
    in the LLM, because we own these strings.
    """
    return text.replace("<input_path>", str(input_path)).replace(
        "<output_path>",
        str(output_path),
    )


def improve_prompt(
    model: OpenAIModel,
    scenario: str,
    input_path: Path,
    output_path: Path,
) -> str:
    """Run the prompt-improvement stage for ``scenario``.

    Loads the stock ``<scenario>_INPUT`` description and its companion
    ``<scenario>_OUTPUT`` few-shot example from
    :class:`GeneratedPrompt`, substitutes concrete dataset and
    screenshot paths into both, formats them into
    :data:`PromptImprovement.USER_PROMPT`, and returns the LLM's
    response content verbatim.

    Args:
        model: configured chat-completions client.
        scenario: one of the CLI ``--scenario`` choices, e.g.
            ``"ml-dvr"``. Hyphens are normalised to underscores and the
            string is upper-cased to match the ``GeneratedPrompt`` member
            naming convention.
        input_path: absolute path to the dataset the generated script
            will read.
        output_path: absolute path where the generated script will write
            its screenshot.

    Returns:
        The improved prompt as plain text.
    """
    scenario_key: str = scenario.replace("-", "_").upper()
    user_input: str = _substitute_paths(
        GeneratedPrompt[f"{scenario_key}_INPUT"],
        input_path=input_path,
        output_path=output_path,
    )
    example_user_input: str = _substitute_paths(
        GeneratedPrompt.STREAM_GLYPH_INPUT,
        input_path=input_path,
        output_path=output_path,
    )
    example_user_output: str = _substitute_paths(
        GeneratedPrompt.STREAM_GLYPH_OUTPUT,
        input_path=input_path,
        output_path=output_path,
    )

    user_prompt: str = PromptImprovement.USER_PROMPT.format(
        user_input=user_input,
        example_user_input=example_user_input,
        example_user_output=example_user_output,
    )
    response: ChatCompletion = model.chat(
        system_prompt=PromptImprovement.SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    return parse_response(response=response)
