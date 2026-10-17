"""Tests for the command-line entry point (argument parsing and exit codes)."""

import io
import runpy
import sys
from types import TracebackType
from typing import Self

import pytest

import pokedex.main
from pokedex import __version__
from pokedex.exceptions import ApiUnavailableError
from pokedex.main import EXIT_ERROR, EXIT_INTERRUPTED, EXIT_OK, main
from tests.doubles import FakeSource


class TestSearchCommand:
    def test_prints_the_pokemon(
        self, fake_source: FakeSource, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["search", "pikachu"], source=fake_source) == EXIT_OK
        assert "#0025  Pikachu" in capsys.readouterr().out

    def test_not_found_goes_to_stderr_with_error_code(
        self, fake_source: FakeSource, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["search", "abc123"], source=fake_source) == EXIT_ERROR
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "Pokémon not found.\n"

    def test_api_error(
        self, fake_source: FakeSource, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fake_source.error = ApiUnavailableError()
        assert main(["search", "pikachu"], source=fake_source) == EXIT_ERROR
        assert "unavailable" in capsys.readouterr().err


class TestListCommand:
    def test_defaults_to_first_page(
        self, fake_source: FakeSource, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["list"], source=fake_source) == EXIT_OK
        assert fake_source.list_calls == [(20, 0)]
        assert "Showing Pokémon 1-20 of 45" in capsys.readouterr().out

    def test_page_and_limit(self, fake_source: FakeSource) -> None:
        main(["list", "--page", "3", "--limit", "5"], source=fake_source)
        assert fake_source.list_calls == [(5, 10)]

    @pytest.mark.parametrize(
        "args",
        [
            ["list", "--page", "0"],
            ["list", "--page", "abc"],
            ["list", "--limit", "0"],
            ["list", "--limit", "101"],
            ["--timeout", "0", "list"],
            ["--timeout", "abc", "list"],
            ["search"],
            ["unknown"],
        ],
    )
    def test_invalid_arguments_exit_with_code_2(
        self, fake_source: FakeSource, args: list[str]
    ) -> None:
        with pytest.raises(SystemExit) as info:
            main(args, source=fake_source)
        assert info.value.code == 2  # argparse's code for usage errors


class TestInteractiveMode:
    def test_no_command_opens_the_menu(
        self,
        fake_source: FakeSource,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO("1\npikachu\n3\n"))
        assert main([], source=fake_source) == EXIT_OK
        out = capsys.readouterr().out
        assert "POKEDEX" in out
        assert "#0025  Pikachu" in out
        assert "Goodbye!" in out

    def test_end_of_input_exits_cleanly(
        self,
        fake_source: FakeSource,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO(""))  # like Ctrl+Z / Ctrl+D
        assert main([], source=fake_source) == EXIT_OK
        assert "Goodbye!" in capsys.readouterr().out

    def test_ctrl_c_exits_without_traceback(
        self,
        fake_source: FakeSource,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr("sys.stdin", _CtrlCStdin())
        assert main([], source=fake_source) == EXIT_INTERRUPTED
        assert "Goodbye!" in capsys.readouterr().out


class _CtrlCStdin:
    """A keyboard where the user presses Ctrl+C at the first prompt.

    ``input()`` reads from ``sys.stdin.readline()`` when stdin is replaced,
    so this tiny class is enough to simulate the key press.
    """

    def readline(self) -> str:
        raise KeyboardInterrupt


class TestWithoutInjectedSource:
    def test_creates_and_closes_a_real_client(
        self, monkeypatch: pytest.MonkeyPatch, fake_source: FakeSource
    ) -> None:
        created: list[_FakeClient] = []

        def factory(timeout: float) -> _FakeClient:
            client = _FakeClient(fake_source, timeout)
            created.append(client)
            return client

        monkeypatch.setattr(pokedex.main, "PokeApiClient", factory)

        assert main(["--timeout", "2.5", "search", "pikachu"]) == EXIT_OK
        assert created[0].timeout == 2.5
        assert created[0].closed


class _FakeClient(FakeSource):
    def __init__(self, source: FakeSource, timeout: float) -> None:
        super().__init__([source.get_pokemon("pikachu")])
        self.timeout = timeout
        self.closed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.closed = True


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert capsys.readouterr().out.strip() == f"pokedex {__version__}"


UTF8_BOM = b"\xef\xbb\xbf"


class _TerminalStdin(io.TextIOWrapper):
    """A stdin that says it is an interactive terminal."""

    def isatty(self) -> bool:
        return True


class TestTextStreams:
    def test_output_is_switched_to_utf8(self, monkeypatch: pytest.MonkeyPatch) -> None:
        stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        monkeypatch.setattr("sys.stdout", stream)
        pokedex.main._configure_text_streams()
        assert sys.stdout.encoding == "utf-8"

    def test_streams_that_are_not_files_are_left_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stream = io.StringIO()  # e.g. a test capturing the output
        monkeypatch.setattr("sys.stdout", stream)
        monkeypatch.setattr("sys.stderr", stream)
        monkeypatch.setattr("sys.stdin", stream)
        pokedex.main._configure_text_streams()
        assert sys.stdout is stream

    def test_piped_input_drops_the_byte_order_mark(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stdin = io.TextIOWrapper(io.BytesIO(UTF8_BOM + b"1\n"), encoding="utf-8")
        monkeypatch.setattr("sys.stdin", stdin)
        pokedex.main._configure_text_streams()
        assert sys.stdin.readline() == "1\n"

    def test_terminal_input_is_left_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stdin = _TerminalStdin(io.BytesIO(b"1\n"), encoding="utf-8")
        monkeypatch.setattr("sys.stdin", stdin)
        pokedex.main._configure_text_streams()
        assert sys.stdin.encoding == "utf-8"

    def test_regression_powershell_pipe_with_bom(
        self,
        fake_source: FakeSource,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Bug found in manual testing: '"3" | py -m pokedex' said "Invalid option"."""
        stdin = io.TextIOWrapper(io.BytesIO(UTF8_BOM + b"3\n"), encoding="utf-8")
        monkeypatch.setattr("sys.stdin", stdin)

        assert main([], source=fake_source) == EXIT_OK

        out = capsys.readouterr().out
        assert "Invalid option" not in out
        assert "Goodbye!" in out


def test_python_dash_m_pokedex(monkeypatch: pytest.MonkeyPatch) -> None:
    """``py -m pokedex`` runs ``pokedex/__main__.py``."""
    monkeypatch.setattr("sys.argv", ["pokedex", "--version"])
    with pytest.raises(SystemExit) as info:
        runpy.run_module("pokedex", run_name="__main__")
    assert info.value.code == 0
