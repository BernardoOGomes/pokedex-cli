"""Interactive menu: the only part of the app that talks to the user.

``PokedexApp`` receives its dependencies instead of creating them:

* ``source`` -- anything with ``get_pokemon`` and ``list_pokemon``
  (the real ``PokeApiClient`` in production, a fake in the tests);
* ``input_func`` / ``output_func`` -- ``input`` and ``print`` by default,
  replaced by scripted functions in the tests.
"""

from collections.abc import Callable
from typing import Protocol

from pokedex.cli.formatting import format_page, format_pokemon
from pokedex.exceptions import PokedexError
from pokedex.models.pokemon import Pokemon, PokemonPage
from pokedex.services.pokeapi import DEFAULT_PAGE_SIZE

MENU = """
=====================
POKEDEX
=====================

1. Search Pokémon
2. List Pokémon
3. Exit
"""

LIST_COMMANDS = """
[n] Next page
[p] Previous page
[q] Quit"""

SEARCH_OPTIONS = {"1", "search", "s"}
LIST_OPTIONS = {"2", "list", "l"}
EXIT_OPTIONS = {"3", "exit", "quit", "q"}


class PokemonSource(Protocol):
    """What the menu needs from a data source (structural typing)."""

    def get_pokemon(self, name_or_id: str | int) -> Pokemon: ...

    def list_pokemon(self, limit: int = ..., offset: int = ...) -> PokemonPage: ...


class PokedexApp:
    def __init__(
        self,
        source: PokemonSource,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> None:
        self._source = source
        self._input = input_func
        self._output = output_func
        self._page_size = page_size

    def run(self) -> None:
        """Show the main menu until the user chooses to exit."""
        while True:
            self._output(MENU)
            choice = self._input("Choose an option: ").strip().lower()
            if choice in SEARCH_OPTIONS:
                self.search()
            elif choice in LIST_OPTIONS:
                self.browse()
            elif choice in EXIT_OPTIONS:
                self._output("Goodbye!")
                return
            else:
                self._output("Invalid option. Please choose 1, 2 or 3.")

    def search(self) -> None:
        """Ask for a name or number and show that Pokemon's details."""
        query = self._input("Enter a Pokémon name or number: ")
        try:
            pokemon = self._source.get_pokemon(query)
        except PokedexError as error:
            self._output(str(error))
            return
        self._output(format_pokemon(pokemon))

    def browse(self) -> None:
        """Page through the Pokemon list with n / p / q."""
        offset = 0
        page: PokemonPage | None = None
        while True:
            if page is None or page.offset != offset:
                try:
                    page = self._source.list_pokemon(
                        limit=self._page_size, offset=offset
                    )
                except PokedexError as error:
                    self._output(str(error))
                    if page is None:  # nothing loaded yet: back to the menu
                        return
                    offset = page.offset  # stay on the page we already have
                    continue
                self._output(format_page(page))
                self._output(LIST_COMMANDS)

            command = self._input("> ").strip().lower()
            if command == "n":
                if page.has_next:
                    offset += self._page_size
                else:
                    self._output("You are already on the last page.")
            elif command == "p":
                if page.has_previous:
                    offset = max(0, offset - self._page_size)
                else:
                    self._output("You are already on the first page.")
            elif command == "q":
                return
            else:
                self._output("Invalid command. Use n, p or q.")
