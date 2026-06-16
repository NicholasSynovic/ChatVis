"""Unit tests for :mod:`chatvis.utils`.

Covers the two notebook-replacement helpers; both are pure, no fixtures
or mocking required.
"""

from chatvis.utils import extract_error_messages, extract_python_code


class TestExtractPythonCode:
    def test_returns_empty_list_when_no_fenced_block(self) -> None:
        assert extract_python_code("just some prose, no fence here") == []

    def test_returns_empty_list_when_fence_lacks_python_tag(self) -> None:
        # ``` ... ``` without the ``python`` language tag must NOT match,
        # otherwise we would extract arbitrary code blocks the LLM emits
        # (shell snippets, JSON, etc.) and feed them to pvpython.
        text: str = "```\nprint('hi')\n```"
        assert extract_python_code(text) == []

    def test_extracts_single_block_and_strips_whitespace(self) -> None:
        text: str = "intro\n```python\n   print('hi')   \n```\noutro"
        assert extract_python_code(text) == ["print('hi')"]

    def test_extracts_multiple_blocks_in_order(self) -> None:
        text: str = (
            "first\n```python\nprint(1)\n```\n"
            "between\n```python\nprint(2)\n```\n"
            "third\n```python\nprint(3)\n```\n"
        )
        assert extract_python_code(text) == [
            "print(1)",
            "print(2)",
            "print(3)",
        ]

    def test_preserves_internal_formatting(self) -> None:
        # Strip only leading/trailing whitespace; indentation inside the
        # block must survive so multi-line scripts round-trip cleanly.
        text: str = "```python\nif True:\n    print('hi')\n    print('bye')\n```"
        [block] = extract_python_code(text)
        assert block == "if True:\n    print('hi')\n    print('bye')"


class TestExtractErrorMessages:
    def test_empty_stderr_returns_empty_list(self) -> None:
        assert extract_error_messages("") == []

    def test_warnings_without_traceback_are_ignored(self) -> None:
        # VTK emits coloured warnings on every run; treating them as
        # errors would loop the repair stage forever.
        stderr: str = "\x1b[33mWarning: deprecated filter\x1b[0m\nSome other notice\n"
        assert extract_error_messages(stderr) == []

    def test_single_traceback_is_extracted(self) -> None:
        stderr: str = (
            "Traceback (most recent call last):\n"
            '  File "/tmp/script.py", line 3, in <module>\n'
            "    raise RuntimeError('boom')\n"
            "RuntimeError: boom\n"
        )
        [message] = extract_error_messages(stderr)
        assert message.startswith('File "/tmp/script.py"')
        assert "RuntimeError: boom" in message

    def test_multiple_tracebacks_are_extracted_in_order(self) -> None:
        stderr: str = (
            "Traceback (most recent call last):\n"
            '  File "/tmp/a.py", line 1, in <module>\n'
            "    raise ValueError('first')\n"
            "ValueError: first\n"
            "noise between\n"
            "Traceback (most recent call last):\n"
            '  File "/tmp/b.py", line 2, in <module>\n'
            "    raise KeyError('second')\n"
            "KeyError: 'second'\n"
        )
        messages: list[str] = extract_error_messages(stderr)
        assert len(messages) == 2
        assert "ValueError: first" in messages[0]
        assert "KeyError: 'second'" in messages[1]

    def test_traceback_surrounded_by_noise_is_still_extracted(self) -> None:
        stderr: str = (
            "\x1b[33mWarning preamble\x1b[0m\n"
            "Traceback (most recent call last):\n"
            '  File "/tmp/x.py", line 7, in <module>\n'
            "    foo()\n"
            "NameError: name 'foo' is not defined\n"
            "trailing junk\n"
        )
        [message] = extract_error_messages(stderr)
        assert "NameError" in message

    def test_silent_vtk_contour_null_is_reported(self) -> None:
        # The ml-iso scenario hit this exact pattern: pvpython exit 0,
        # no traceback, but the contour ran on empty input.
        stderr: str = (
            "\x1b[0m\x1b[33m(   0.478s) [paraview        ]      "
            "vtkDataReader.cxx:1507  WARN| Error reading binary data!\x1b[0m\n"
            "\x1b[0m\x1b[2m(   0.560s) [paraview        ] "
            "vtkPVContourFilter.cxx:106   INFO| \x1b[0mContour array is null.\x1b[0m\n"
        )
        messages: list[str] = extract_error_messages(stderr)
        # Both patterns match -- we want at least the contour-null one.
        assert any("Contour array is null" in m for m in messages)
        assert any("Error reading binary data" in m for m in messages)

    def test_silent_failure_suppressed_when_traceback_present(self) -> None:
        # A real Python traceback must not be masked by a downstream
        # VTK warning. Only the traceback is returned.
        stderr: str = (
            "Traceback (most recent call last):\n"
            '  File "/tmp/x.py", line 1, in <module>\n'
            "    raise RuntimeError('boom')\n"
            "RuntimeError: boom\n"
            "Contour array is null.\n"
        )
        messages: list[str] = extract_error_messages(stderr)
        assert len(messages) == 1
        assert "RuntimeError: boom" in messages[0]

    def test_silent_failure_pattern_substring_only(self) -> None:
        # Unrelated stderr lines that mention none of the silent-failure
        # tokens are still ignored.
        stderr: str = "(  0.1s) [paraview] some.cxx:1 INFO| pipeline ok\n"
        assert extract_error_messages(stderr) == []
