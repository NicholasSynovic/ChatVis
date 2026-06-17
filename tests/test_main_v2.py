"""Unit tests for the v2 orchestration helpers in :mod:`chatvis.main`.

A real v2 run needs a live Argo LLM, a ``pvpython`` binary, and (on a
cold cache) a sentence-transformers model download, so those are all
stubbed here. The tests assert wiring: that the scenario query is built
from :class:`UserPrompts`, that the stages are called in order, and that
the exit codes match the documented contract.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

import chatvis.main as main
from chatvis.cli import SCENARIOS


class TestBuildV2Query:
    def test_uses_user_prompt_for_scenario(self) -> None:
        query: str = main._build_v2_query(
            scenario="stream-glyph",
            input_path=Path("/data/disk.ex2"),
            output_path=Path("/out/shot.png"),
        )
        # The UserPrompts.STREAM_GLYPH text mentions streamlines and the
        # substituted paths.
        assert "streamlines" in query.lower()
        assert "/data/disk.ex2" in query
        assert "/out/shot.png" in query
        assert "{input_path}" not in query
        assert "{output_path}" not in query

    def test_every_cli_scenario_resolves(self) -> None:
        # A scenario added to the CLI without a matching UserPrompts
        # member would raise KeyError here.
        for scenario in SCENARIOS:
            query: str = main._build_v2_query(
                scenario=scenario,
                input_path=Path("/in"),
                output_path=Path("/out"),
            )
            assert query


def _make_cli_args(tmp_path: Path) -> SimpleNamespace:
    data_file: Path = tmp_path / "disk.ex2"
    data_file.write_text("", encoding="utf-8")
    return SimpleNamespace(
        scenario="stream-glyph",
        data_filepath=data_file,
        screenshot_path=tmp_path / "shot.png",
        faiss_index=tmp_path / "faiss.index",
        metadata_lookup=tmp_path / "metadata_lookup.pickle",
        top_k=5,
        max_repair_attempts=3,
        username="user",
        model="gpt4o",
        endpoint="http://example.invalid",
        argo=False,
        pvpython=Path("/usr/bin/pvpython"),
    )


class TestRunV2Pipeline:
    def test_clean_first_attempt_returns_ok(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cli_args = _make_cli_args(tmp_path)
        calls: list[str] = []

        monkeypatch.setattr(main, "OpenAIModel", lambda **_: object())
        monkeypatch.setattr(
            main,
            "_retrieve_snippets",
            lambda **_: (calls.append("retrieve"), "[]")[1],
        )

        def fake_generate(**_: object) -> str:
            calls.append("generate")
            return "```python\nprint('hi')\n```"

        monkeypatch.setattr(main, "generate_code_v2", fake_generate)

        def fake_run(**_: object) -> tuple[list[str], str]:
            calls.append("run")
            return [], "stdout text"

        monkeypatch.setattr(main, "_run_and_extract_errors", fake_run)

        exit_code: int = main.run_v2_pipeline(
            cli_args=cli_args,  # type: ignore[arg-type]
            logger=main.logging.getLogger("test"),
        )

        assert exit_code == main._EXIT_OK
        assert calls == ["retrieve", "generate", "run"]
        # The generated script was persisted next to the screenshot.
        assert (tmp_path / "shot.py").read_text(encoding="utf-8") == "print('hi')"

    def test_missing_data_file_returns_config_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cli_args = _make_cli_args(tmp_path)
        cli_args.data_filepath = tmp_path / "does-not-exist.ex2"

        exit_code: int = main.run_v2_pipeline(
            cli_args=cli_args,  # type: ignore[arg-type]
            logger=main.logging.getLogger("test"),
        )
        assert exit_code == main._EXIT_CONFIG_ERROR

    def test_repair_loop_recovers(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cli_args = _make_cli_args(tmp_path)

        monkeypatch.setattr(main, "OpenAIModel", lambda **_: object())
        monkeypatch.setattr(main, "_retrieve_snippets", lambda **_: "[]")
        monkeypatch.setattr(
            main,
            "generate_code_v2",
            lambda **_: "```python\nbroken\n```",
        )
        monkeypatch.setattr(
            main,
            "improve_code_v2",
            lambda **_: "```python\nfixed\n```",
        )

        runs: list[int] = []

        def fake_run(**_: object) -> tuple[list[str], str]:
            runs.append(1)
            # Fail on the first execution, succeed on the repair run.
            if len(runs) == 1:
                return ["Traceback: boom"], ""
            return [], ""

        monkeypatch.setattr(main, "_run_and_extract_errors", fake_run)

        exit_code: int = main.run_v2_pipeline(
            cli_args=cli_args,  # type: ignore[arg-type]
            logger=main.logging.getLogger("test"),
        )

        assert exit_code == main._EXIT_OK
        assert len(runs) == 2
        assert (tmp_path / "shot.py").read_text(encoding="utf-8") == "fixed"
