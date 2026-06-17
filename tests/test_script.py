"""Unit tests for :mod:`chatvis.script`."""

from pathlib import Path

import pytest

from chatvis.script import derive_script_path, first_python_block, write_script


class TestDeriveScriptPath:
    def test_png_to_py_swap(self) -> None:
        assert derive_script_path(Path("/out/foo.png")) == Path("/out/foo.py")

    def test_nested_directory_preserved(self) -> None:
        result: Path = derive_script_path(Path("/a/b/c/scene.jpg"))
        assert result == Path("/a/b/c/scene.py")

    def test_path_without_suffix_gets_py_appended(self) -> None:
        # ``Path.with_suffix(".py")`` on a suffixless path appends rather
        # than replacing. Pin that behaviour so callers can rely on it.
        assert derive_script_path(Path("/out/foo")) == Path("/out/foo.py")


class TestFirstPythonBlock:
    def test_raises_value_error_when_no_block(self) -> None:
        with pytest.raises(ValueError, match="python"):
            first_python_block("no fence in this reply")

    def test_returns_single_block(self) -> None:
        assert first_python_block("```python\nprint('hi')\n```") == "print('hi')"

    def test_returns_first_when_multiple_blocks_present(self) -> None:
        text: str = "```python\nfirst\n```\nmiddle\n```python\nsecond\n```"
        assert first_python_block(text) == "first"


class TestWriteScript:
    def test_writes_content_and_returns_path(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "scene.py"
        result: Path = write_script("print('hi')\n", target)
        assert result == target
        assert target.read_text(encoding="utf-8") == "print('hi')\n"

    def test_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "nested" / "deeper" / "scene.py"
        write_script("x = 1\n", target)
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "x = 1\n"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "scene.py"
        target.write_text("OLD", encoding="utf-8")
        write_script("NEW", target)
        assert target.read_text(encoding="utf-8") == "NEW"
