"""Tests for the interactive menu, driven by scripted input.

``ScriptedInput`` plays the role of the keyboard: each call to it returns the
next answer of a list. The output is collected in a list of strings instead
of being printed, so the tests can assert on what the user would see.
"""

import pytest

from pokedex.cli.menu import MENU, PokedexApp
from pokedex.exceptions import ApiTimeoutError, ApiUnavailableError
from tests.doubles import FakeSource


class ScriptedInput:
    def __init__(self, *answers: str) -> None:
        self._answers = list(answers)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._answers:
            raise AssertionError(f"unexpected extra prompt: {prompt!r}")
        return self._answers.pop(0)


class Output:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def __call__(self, message: str) -> None:
        self.messages.append(message)

    @property
    def text(self) -> str:
        return "\n".join(self.messages)


def run_app(source: FakeSource, *answers: str, page_size: int = 20) -> Output:
    """Run the whole menu with the given keyboard answers."""
    output = Output()
    app = PokedexApp(
        source,
        input_func=ScriptedInput(*answers),
        output_func=output,
        page_size=page_size,
    )
    app.run()
    return output


class TestMainMenu:
    def test_shows_menu_and_exits(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "3")
        assert output.messages == [MENU, "Goodbye!"]

    def test_menu_matches_the_spec(self) -> None:
        for line in ["POKEDEX", "1. Search Pokémon", "2. List Pokémon", "3. Exit"]:
            assert line in MENU

    @pytest.mark.parametrize("choice", ["4", "0", "", "abc", "1 2"])
    def test_invalid_option_shows_message_and_menu_again(
        self, fake_source: FakeSource, choice: str
    ) -> None:
        output = run_app(fake_source, choice, "3")
        assert output.messages == [
            MENU,
            "Invalid option. Please choose 1, 2 or 3.",
            MENU,
            "Goodbye!",
        ]

    @pytest.mark.parametrize("choice", ["exit", "EXIT", "q", " 3 "])
    def test_exit_aliases(self, fake_source: FakeSource, choice: str) -> None:
        assert run_app(fake_source, choice).messages[-1] == "Goodbye!"


class TestSearch:
    def test_shows_the_pokemon(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "1", "pikachu", "3")
        assert "#0025  Pikachu" in output.text
        assert "Speed      90" in output.text

    def test_search_by_number(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "1", "25", "3")
        assert "#0025  Pikachu" in output.text

    @pytest.mark.parametrize("choice", ["search", "s"])
    def test_search_aliases(self, fake_source: FakeSource, choice: str) -> None:
        output = run_app(fake_source, choice, "pikachu", "3")
        assert "Pikachu" in output.text

    def test_not_found(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "1", "abc123", "3")
        assert "Pokémon not found." in output.messages

    def test_api_error_shows_message_and_returns_to_menu(
        self, fake_source: FakeSource
    ) -> None:
        fake_source.error = ApiTimeoutError(10)
        output = run_app(fake_source, "1", "pikachu", "3")
        assert str(ApiTimeoutError(10)) in output.messages
        assert output.messages[-1] == "Goodbye!"


class TestBrowse:
    def test_first_page(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "2", "q", "3")
        assert "Showing Pokémon 1-20 of 45 (page 1/3)" in output.text
        assert " 1. Pokemon 1" in output.text
        assert "20. Pokemon 20" in output.text
        assert "[n] Next page" in output.text
        assert fake_source.list_calls == [(20, 0)]

    def test_next_and_previous(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "2", "n", "p", "q", "3")
        assert fake_source.list_calls == [(20, 0), (20, 20), (20, 0)]
        assert "Showing Pokémon 21-40 of 45" in output.text

    def test_last_page_is_partial(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "2", "n", "n", "q", "3")
        assert "Showing Pokémon 41-45 of 45" in output.text

    def test_previous_on_first_page(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "2", "p", "q", "3")
        assert "You are already on the first page." in output.messages
        assert fake_source.list_calls == [(20, 0)]  # no extra request

    def test_next_on_last_page(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "2", "n", "n", "n", "q", "3")
        assert "You are already on the last page." in output.messages
        assert fake_source.list_calls == [(20, 0), (20, 20), (20, 40)]

    @pytest.mark.parametrize("command", ["x", "", "next", "1"])
    def test_invalid_command(self, fake_source: FakeSource, command: str) -> None:
        output = run_app(fake_source, "2", command, "q", "3")
        assert "Invalid command. Use n, p or q." in output.messages

    def test_commands_are_case_insensitive(self, fake_source: FakeSource) -> None:
        run_app(fake_source, "2", " N ", "Q", "3")
        assert fake_source.list_calls == [(20, 0), (20, 20)]

    def test_quit_returns_to_main_menu(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "list", "q", "3")
        assert output.messages[-2:] == [MENU, "Goodbye!"]

    def test_custom_page_size(self, fake_source: FakeSource) -> None:
        output = run_app(fake_source, "2", "n", "q", "3", page_size=10)
        assert "Showing Pokémon 11-20 of 45" in output.text

    def test_error_on_first_page_returns_to_menu(self, fake_source: FakeSource) -> None:
        fake_source.error = ApiUnavailableError()
        output = run_app(fake_source, "2", "3")
        assert str(ApiUnavailableError()) in output.messages

    def test_error_on_next_page_keeps_current_page(
        self, fake_source: FakeSource
    ) -> None:
        # The network fails once when loading the second page.
        fake_source.page_errors[20] = ApiUnavailableError()

        output = run_app(fake_source, "2", "n", "n", "q", "3")

        assert str(ApiUnavailableError()) in output.messages
        # first page, failed attempt at offset 20, then a successful retry
        assert fake_source.list_calls == [(20, 0), (20, 20), (20, 20)]
        assert "Showing Pokémon 21-40 of 45" in output.text
