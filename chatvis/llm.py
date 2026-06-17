"""LLM orchestration for ChatVis.

Provides an OpenAI-compatible chat-completions wrapper configured for
deterministic, reproducible runs against Argonne's Argo endpoint, plus
the three pipeline-stage helpers:

* :func:`improve_prompt` turns a stock scenario description into an
  LLM-improved prompt suitable for code generation.
* :func:`generate_code` asks the LLM for a ParaView script implementing
  the improved prompt.
* :func:`improve_code` is the repair stage: given a broken script and
  the captured ``pvpython`` errors, ask the LLM to fix the failing line
  without rewriting the rest of the script.

The v2 (RAG) pipeline reuses :class:`OpenAIModel` and :func:`parse_response`
but has its own two stage helpers, :func:`generate_code_v2` and
:func:`improve_code_v2`. v2 has no prompt-improvement stage: the retrieved
ParaView snippets are injected into the *user* prompt at code-generation
time (see :class:`chatvis.v2.prompts.code_generation.CodeGeneration`).

Prompt source-of-truth split:

* The *user's own* scenario input comes from :class:`UserPrompts`,
  which carries ``{input_path}`` / ``{output_path}`` placeholders
  consumed by Python's :py:meth:`str.format`.
* The *few-shot example pair* (input shown to the LLM plus the desired
  improved output) comes from :class:`GeneratedPrompt`, which carries
  ``<input_path>`` / ``<output_path>`` angle-bracket sentinels consumed
  by :func:`_substitute_paths`. The two conventions deliberately coexist
  so the cleaner ``.format`` path can be used for new authored prompts
  without rewriting the legacy few-shot data.
"""

import logging
from logging import Logger
from pathlib import Path

import httpx
from openai import Client
from openai.types.chat import ChatCompletion

from chatvis.v1.documents.prompts import GeneratedPrompt
from chatvis.v1.prompts.code_generation import CodeGeneration
from chatvis.v1.prompts.code_improvement import CodeImprovement
from chatvis.v1.prompts.prompt_improvement import PromptImprovement
from chatvis.v1.prompts.user_prompts import UserPrompts
from chatvis.v2.prompts.code_generation import CodeGeneration as CodeGenerationV2
from chatvis.v2.prompts.code_improvement import CodeImprovement as CodeImprovementV2

# Few-shot pair to show for each scenario during prompt improvement.
# Rule: pick a pair from a *different* scenario family than the one
# being asked about, so the LLM is not handed back its own answer.
# Today only two distinct families exist (the stream-glyph family
# covering ML_DVR / ML_ISO / ML_SLICE_ISO / STREAM_GLYPH, and the
# points-surf-clip family), so this collapses to a binary toggle.
_FEW_SHOT_KEY_BY_SCENARIO: dict[str, str] = {
    "ml-dvr": "POINTS_SURF_CLIP",
    "ml-iso": "POINTS_SURF_CLIP",
    "ml-slice-iso": "POINTS_SURF_CLIP",
    "stream-glyph": "POINTS_SURF_CLIP",
    "points-surf-clip": "STREAM_GLYPH",
}

# Defaults chosen for reproducibility. ``seed`` is best-effort per the
# OpenAI spec; the returned ``system_fingerprint`` lets a caller detect
# when the backend has changed in a way that may invalidate determinism.
DEFAULT_SEED: int = 42
DEFAULT_TEMPERATURE: float = 0.0
DEFAULT_TOP_P: float = 1.0
DEFAULT_N: int = 1

# Host header expected by Argonne's internal Argo gateway. Only sent when
# the client is constructed with ``argo=True`` (see ``OpenAIModel``).
ARGO_HOST: str = "apps.inside.anl.gov"


class OpenAIModel:
    """Thin wrapper around the OpenAI Chat Completions API.

    Argo authenticates by ANL username supplied via the OpenAI client's
    ``api_key`` parameter. The name ``api_key`` mirrors that contract.

    All sampling parameters default to deterministic values so two runs
    issued against the same backend revision should return identical
    content. Override per call only when nondeterminism is desired.

    The ``argo`` flag opts into the quirks of Argonne's internal Argo
    gateway: it disables TLS certificate verification and sends a
    ``Host: apps.inside.anl.gov`` header. It is **off by default** so the
    wrapper talks to standards-compliant OpenAI-compatible endpoints
    securely; enable it only when targeting the internal Argo endpoint.
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
        argo: bool = False,
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
        self.argo: bool = argo
        default_headers: dict[str, str] = {"Host": ARGO_HOST} if argo else {}
        self.client: Client = Client(
            base_url=self.endpoint,
            api_key=api_key,
            default_headers=default_headers,
            http_client=httpx.Client(verify=not argo),
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
            stream=False,
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


def improve_prompt_v1(
    model: OpenAIModel,
    scenario: str,
    input_path: Path,
    output_path: Path,
) -> str:
    """Run the prompt-improvement stage for ``scenario``.

    Loads the user's scenario description from :class:`UserPrompts`
    (``{input_path}`` / ``{output_path}`` substituted via
    :py:meth:`str.format`) plus a few-shot ``_INPUT`` / ``_OUTPUT`` pair
    from :class:`GeneratedPrompt` (``<input_path>`` / ``<output_path>``
    sentinels substituted via :func:`_substitute_paths`). The few-shot
    pair is chosen from a *different* scenario family via
    :data:`_FEW_SHOT_KEY_BY_SCENARIO` so the LLM is never shown the
    answer for the scenario it is being asked to improve. All three
    strings are then formatted into :data:`PromptImprovement.USER_PROMPT`.

    Args:
        model: configured chat-completions client.
        scenario: one of the CLI ``--scenario`` choices, e.g.
            ``"ml-dvr"``. Hyphens are normalised to underscores and the
            string is upper-cased to match the ``UserPrompts`` and
            ``GeneratedPrompt`` member naming convention.
        input_path: absolute path to the dataset the generated script
            will read.
        output_path: absolute path where the generated script will write
            its screenshot.

    Returns:
        The improved prompt as plain text.

    Raises:
        ValueError: if ``scenario`` has no entry in
            :data:`_FEW_SHOT_KEY_BY_SCENARIO`.
        KeyError: if :class:`UserPrompts` has no member matching
            ``scenario`` (e.g. a new scenario was added to the CLI
            choices but the corresponding ``UserPrompts`` entry was
            forgotten).
    """
    scenario_key: str = scenario.replace("-", "_").upper()
    try:
        few_shot_key: str = _FEW_SHOT_KEY_BY_SCENARIO[scenario]
    except KeyError as exc:
        raise ValueError(
            f"No few-shot example configured for scenario {scenario!r}"
        ) from exc

    user_input: str = UserPrompts[scenario_key].format(
        input_path=input_path,
        output_path=output_path,
    )
    example_user_input: str = _substitute_paths(
        GeneratedPrompt[f"{few_shot_key}_INPUT"],
        input_path=input_path,
        output_path=output_path,
    )
    example_user_output: str = _substitute_paths(
        GeneratedPrompt[f"{few_shot_key}_OUTPUT"],
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


def generate_code_v1(model: OpenAIModel, improved_prompt: str) -> str:
    """Run the code-generation stage.

    Sends :data:`CodeGeneration.SYSTEM_PROMPT` (which embeds every
    ParaView code snippet from :class:`CodeSnippet` inside Markdown
    fenced blocks at class-definition time) together with the
    LLM-improved scenario prompt produced by :func:`improve_prompt`.

    The LLM's reply is returned verbatim. It is expected to contain at
    least one ``` ```python ... ``` ``` block; extraction and on-disk
    persistence are handled by downstream helpers, not here.

    Args:
        model: configured chat-completions client.
        improved_prompt: the natural-language scenario description, as
            returned by :func:`improve_prompt`.

    Returns:
        The raw LLM response content (Markdown text including one or
        more fenced Python blocks).
    """
    user_prompt: str = CodeGeneration.USER_PROMPT.format(prompt=improved_prompt)
    response: ChatCompletion = model.chat(
        system_prompt=CodeGeneration.SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    return parse_response(response=response)


def improve_code_v1(
    model: OpenAIModel,
    improved_prompt: str,
    broken_script: str,
    errors: str,
    stdout: str = "",
) -> str:
    """Run the code-improvement (repair) stage.

    Issued by the orchestrator's repair loop after a ``pvpython`` run
    surfaces at least one traceback. Sends the focused-fix
    :data:`CodeImprovement.SYSTEM_PROMPT` together with the captured
    error text, the script that produced it, the previous run's
    standard output, and the original improved prompt so the LLM has
    the full context needed to fix only the failing line.

    Args:
        model: configured chat-completions client.
        improved_prompt: the natural-language scenario description, as
            returned by :func:`improve_prompt` and previously passed to
            :func:`generate_code`. Re-supplied verbatim so the repair
            stage knows what the script was *meant* to achieve.
        broken_script: the on-disk Python script that ``pvpython``
            failed on, i.e. the output of
            :func:`chatvis.script.first_python_block` after
            :func:`generate_code`. Pass the extracted script rather than
            the raw LLM response so the LLM sees exactly what was
            executed.
        errors: the failure text to show the LLM. Typically
            ``"\\n".join(extract_error_messages(stderr))`` so that VTK's
            ANSI-coloured noise is stripped, but any string is accepted;
            callers may pass raw stderr if they want the LLM to see the
            full context.
        stdout: the captured standard-output text from the previous
            ``pvpython`` run. Defaults to the empty string. Threaded
            into the user prompt so the LLM can read any diagnostic
            information that the previous script printed (for example,
            the list of available PointData array names produced by a
            previous repair iteration), rather than asking a human to
            inspect it and edit the script.

    Returns:
        The raw LLM response content (Markdown text including one or
        more fenced Python blocks). Extraction is the caller's job, as
        with :func:`generate_code`.
    """
    user_prompt: str = CodeImprovement.USER_PROMPT.format(
        errors=errors,
        script=broken_script,
        stdout=stdout,
        prompt=improved_prompt,
    )
    response: ChatCompletion = model.chat(
        system_prompt=CodeImprovement.SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    return parse_response(response=response)


def generate_code_v2(
    model: OpenAIModel,
    prompt: str,
    code_snippets: str,
) -> str:
    """Run the v2 (RAG) code-generation stage.

    Unlike v1, there is no prompt-improvement step: the user's scenario
    description is sent verbatim alongside the ParaView snippets
    retrieved from the FAISS index. Both are formatted into
    :data:`chatvis.v2.prompts.code_generation.CodeGeneration.USER_PROMPT`
    (``{prompt}`` plus ``{code_snippets}``); the static guidance lives in
    that class's ``SYSTEM_PROMPT``.

    Args:
        model: configured chat-completions client.
        prompt: the scenario description, typically built from
            :class:`chatvis.v1.prompts.user_prompts.UserPrompts`.
        code_snippets: the retrieved example operations, already
            serialised into a single string ready to drop into the
            ``json`` fence of the user prompt.

    Returns:
        The raw LLM response content (Markdown text including one or
        more fenced Python blocks). Extraction is the caller's job.
    """
    user_prompt: str = CodeGenerationV2.USER_PROMPT.format(
        prompt=prompt,
        code_snippets=code_snippets,
    )
    response: ChatCompletion = model.chat(
        system_prompt=CodeGenerationV2.SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    return parse_response(response=response)


def improve_code_v2(
    model: OpenAIModel,
    broken_script: str,
    errors: str,
    stdout: str = "",
) -> str:
    """Run the v2 (RAG) code-improvement (repair) stage.

    The repair user prompt
    (:data:`chatvis.v2.prompts.code_improvement.CodeImprovement.USER_PROMPT`)
    carries only ``{errors}`` / ``{script}`` / ``{stdout}``; the retrieved
    snippets are not re-injected here. The system prompt is reused from
    :data:`chatvis.v2.prompts.code_generation.CodeGeneration.SYSTEM_PROMPT`
    so the repair stage operates under the same visualization-scripting
    guidance as generation.

    Args:
        model: configured chat-completions client.
        broken_script: the on-disk Python script that ``pvpython`` failed
            on. Pass the extracted script rather than the raw LLM
            response so the LLM sees exactly what was executed.
        errors: the failure text to show the LLM, typically
            ``"\\n".join(extract_error_messages(stderr))``.
        stdout: the captured standard-output text from the previous
            ``pvpython`` run. Defaults to the empty string. Threaded into
            the user prompt so the LLM can read any diagnostic
            information the previous script printed.

    Returns:
        The raw LLM response content (Markdown text including one or
        more fenced Python blocks). Extraction is the caller's job.
    """
    user_prompt: str = CodeImprovementV2.USER_PROMPT.format(
        errors=errors,
        script=broken_script,
        stdout=stdout,
    )
    response: ChatCompletion = model.chat(
        system_prompt=CodeGenerationV2.SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    return parse_response(response=response)
