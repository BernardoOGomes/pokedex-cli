"""Entry point: parses the command line and wires the layers together.

    pokedex                      -> interactive menu
    pokedex search pikachu       -> print one Pokemon and exit
    pokedex list --page 2        -> print one page of the list and exit

This is the "composition root": the only place that creates the real
``PokeApiClient`` and hands it to the CLI.
"""

import argparse
import io
import sys
from collections.abc import Sequence

from pokedex import __version__
from pokedex.cli.formatting import format_page, format_pokemon
from pokedex.cli.menu import PokedexApp, PokemonSource
from pokedex.exceptions import PokedexError
from pokedex.services.pokeapi import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    MAX_PAGE_SIZE,
    PokeApiClient,
)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130  # shell convention for "stopped with Ctrl+C"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pokedex",
        description="Search and browse Pokémon using the PokéAPI. "
        "Run without a command to open the interactive menu.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=DEFAULT_TIMEOUT,
        help=f"seconds to wait for the API (default: {DEFAULT_TIMEOUT:g})",
    )
    commands = parser.add_subparsers(dest="command")

    search = commands.add_parser("search", help="show the details of one Pokémon")
    search.add_argument("name_or_id", help="Pokémon name or number, e.g. pikachu or 25")

    listing = commands.add_parser("list", help="show one page of the Pokémon list")
    listing.add_argument(
        "--page", type=_positive_int, default=1, help="page number (default: 1)"
    )
    listing.add_argument(
        "--limit",
        type=_page_size,
        default=DEFAULT_PAGE_SIZE,
        help=f"Pokémon per page, 1-{MAX_PAGE_SIZE} (default: {DEFAULT_PAGE_SIZE})",
    )
    return parser


def main(argv: Sequence[str] | None = None, source: PokemonSource | None = None) -> int:
    """Run the application and return the process exit code.

    ``source`` lets tests inject a fake client; in production it is ``None``
    and a real ``PokeApiClient`` is created (and closed at the end).
    """
    _configure_text_streams()
    args = build_parser().parse_args(argv)
    if source is not None:
        return _run(args, source)
    with PokeApiClient(timeout=args.timeout) as client:
        return _run(args, client)


def _run(args: argparse.Namespace, source: PokemonSource) -> int:
    try:
        if args.command == "search":
            print(format_pokemon(source.get_pokemon(args.name_or_id)))
        elif args.command == "list":
            offset = (args.page - 1) * args.limit
            print(format_page(source.list_pokemon(limit=args.limit, offset=offset)))
        else:
            PokedexApp(source).run()
    except PokedexError as error:
        print(error, file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:  # Ctrl+C
        print("\nGoodbye!")
        return EXIT_INTERRUPTED
    except EOFError:  # Ctrl+Z / Ctrl+D, or the end of piped input
        print("\nGoodbye!")
    return EXIT_OK


def _configure_text_streams() -> None:
    """Make "é" and piped input work the same in every terminal.

    * Output: in an interactive Windows console Python already writes
      Unicode, but redirected output falls back to the legacy code page
      (cp1252), which other tools then misread. We always write UTF-8.
    * Input: when text is piped in (``"1" | py -m pokedex``), Windows
      PowerShell 5.1 puts an invisible byte order mark (BOM) before it, so
      the first answer would be "\\ufeff1" instead of "1". The "utf-8-sig"
      codec reads UTF-8 and drops that mark.
    """
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    if isinstance(sys.stdin, io.TextIOWrapper) and not sys.stdin.isatty():
        sys.stdin.reconfigure(encoding="utf-8-sig")


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or greater")
    return value


def _page_size(text: str) -> int:
    value = _positive_int(text)
    if value > MAX_PAGE_SIZE:
        raise argparse.ArgumentTypeError(f"must be {MAX_PAGE_SIZE} or less")
    return value


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value
