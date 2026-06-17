"""Unit tests for the pure helpers in :mod:`chatvis.llm`.

The ``OpenAIModel`` wrapper and the three pipeline-stage helpers are
not covered here because they require either a live LLM or a non-trivial
stub of the OpenAI client; that belongs in an integration suite.
"""

from pathlib import Path
from types import SimpleNamespace

from chatvis.llm import (
    _FEW_SHOT_KEY_BY_SCENARIO,
    _substitute_paths,
    generate_code_v2,
    improve_code_v2,
    parse_response,
)
from chatvis.v1.documents.prompts import GeneratedPrompt


class _CapturingModel:
    """Stub ``OpenAIModel`` that records the prompts it is handed.

    ``chat`` returns a minimal ``ChatCompletion``-shaped object so the
    real :func:`parse_response` can extract its content unchanged.
    """

    def __init__(self, content: str = "ok") -> None:
        self.content: str = content
        self.system_prompt: str | None = None
        self.user_prompt: str | None = None

    def chat(self, system_prompt: str, user_prompt: str):  # noqa: ANN201
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self.content)),
            ],
        )


class TestSubstitutePaths:
    def test_both_sentinels_replaced(self) -> None:
        text: str = "read <input_path>; write <output_path>"
        result: str = _substitute_paths(
            text,
            input_path=Path("/a/b.ex2"),
            output_path=Path("/c/d.png"),
        )
        assert result == "read /a/b.ex2; write /c/d.png"

    def test_text_without_sentinels_unchanged(self) -> None:
        text: str = "plain text, no sentinels"
        result: str = _substitute_paths(
            text,
            input_path=Path("/a"),
            output_path=Path("/b"),
        )
        assert result == text

    def test_does_not_touch_python_format_placeholders(self) -> None:
        # The two prompt-source conventions must NOT cross-pollinate:
        # ``_substitute_paths`` is only responsible for angle-bracket
        # sentinels, leaving any stray ``{input_path}`` for downstream
        # ``str.format`` to handle (or fail loudly on).
        text: str = "read {input_path}; write <output_path>"
        result: str = _substitute_paths(
            text,
            input_path=Path("/a"),
            output_path=Path("/b"),
        )
        assert result == "read {input_path}; write /b"

    def test_multiple_occurrences_all_replaced(self) -> None:
        text: str = "<input_path> and <input_path> again"
        result: str = _substitute_paths(
            text,
            input_path=Path("/x"),
            output_path=Path("/y"),
        )
        assert result == "/x and /x again"


class TestParseResponse:
    def test_returns_content_when_present(self) -> None:
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="hello")),
            ],
        )
        assert parse_response(response) == "hello"  # type: ignore[arg-type]

    def test_returns_empty_string_when_content_is_none(self) -> None:
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=None)),
            ],
        )
        assert parse_response(response) == ""  # type: ignore[arg-type]


class TestFewShotKeyByScenario:
    """Invariants documented in AGENTS.md.

    Editing this dict carelessly silently breaks the few-shot strategy
    (either by pairing a scenario with itself, or by pointing at a
    GeneratedPrompt member that does not exist).
    """

    def test_covers_every_cli_scenario(self) -> None:
        # Keep in lock-step with ``chatvis.cli.SCENARIOS``. Hard-coding
        # the expected set here is intentional: a silent drop from the
        # mapping would otherwise just raise ``ValueError`` at runtime.
        expected: set[str] = {
            "ml-dvr",
            "ml-iso",
            "ml-slice-iso",
            "stream-glyph",
            "points-surf-clip",
        }
        assert set(_FEW_SHOT_KEY_BY_SCENARIO) == expected

    def test_no_self_referential_mapping(self) -> None:
        # If ``ml-dvr`` mapped to ``ML_DVR`` the LLM would be handed its
        # own answer as the few-shot example, defeating the purpose.
        for scenario, key in _FEW_SHOT_KEY_BY_SCENARIO.items():
            assert key != scenario.replace("-", "_").upper(), (
                f"scenario {scenario!r} maps to its own few-shot {key!r}"
            )

    def test_every_target_resolves_to_a_generated_prompt(self) -> None:
        for key in _FEW_SHOT_KEY_BY_SCENARIO.values():
            # Both the ``_INPUT`` and ``_OUTPUT`` members must exist;
            # ``improve_prompt`` derefs both.
            assert f"{key}_INPUT" in GeneratedPrompt.__members__
            assert f"{key}_OUTPUT" in GeneratedPrompt.__members__


class TestGenerateCodeV2:
    def test_injects_prompt_and_snippets_into_user_prompt(self) -> None:
        model = _CapturingModel(content="```python\npass\n```")
        result: str = generate_code_v2(
            model=model,  # type: ignore[arg-type]
            prompt="DESCRIBE THE SCENARIO",
            code_snippets='[{"name": "foo"}]',
        )
        assert result == "```python\npass\n```"
        assert "DESCRIBE THE SCENARIO" in model.user_prompt  # type: ignore[operator]
        assert '[{"name": "foo"}]' in model.user_prompt  # type: ignore[operator]
        # No unfilled placeholders left behind.
        assert "{prompt}" not in model.user_prompt  # type: ignore[operator]
        assert "{code_snippets}" not in model.user_prompt  # type: ignore[operator]


class TestImproveCodeV2:
    def test_injects_errors_script_stdout_into_user_prompt(self) -> None:
        model = _CapturingModel(content="fixed")
        result: str = improve_code_v2(
            model=model,  # type: ignore[arg-type]
            broken_script="SCRIPT BODY",
            errors="BOOM",
            stdout="DIAGNOSTIC",
        )
        assert result == "fixed"
        assert "BOOM" in model.user_prompt  # type: ignore[operator]
        assert "SCRIPT BODY" in model.user_prompt  # type: ignore[operator]
        assert "DIAGNOSTIC" in model.user_prompt  # type: ignore[operator]
        assert "{errors}" not in model.user_prompt  # type: ignore[operator]
        assert "{script}" not in model.user_prompt  # type: ignore[operator]
        assert "{stdout}" not in model.user_prompt  # type: ignore[operator]

    def test_stdout_defaults_to_empty_string(self) -> None:
        model = _CapturingModel()
        improve_code_v2(
            model=model,  # type: ignore[arg-type]
            broken_script="s",
            errors="e",
        )
        # The {stdout} placeholder must still be consumed even when the
        # caller omits stdout.
        assert "{stdout}" not in model.user_prompt  # type: ignore[operator]
