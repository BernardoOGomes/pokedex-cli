# Pokedex CLI

[![CI](https://github.com/BernardoOGomes/pokedex-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/BernardoOGomes/pokedex-cli/actions/workflows/ci.yml)

A command-line Pokédex written in Python. It searches and lists Pokémon using the
public [PokéAPI](https://pokeapi.co/), showing types, height, weight, abilities
and base stats.

```text
========================================
#0025  Pikachu
========================================
Types:     Electric
Height:    0.4 m
Weight:    6.0 kg
Abilities: Static, Lightning Rod (hidden)

Base stats
  HP         35  ###
  Attack     55  #####
  Defense    40  ####
  Sp. Atk    50  #####
  Sp. Def    50  #####
  Speed      90  #########
  Total     320
```

## Features

- **Search** by name or number: `pikachu`, `25`, `025`, `Mr. Mime`, `Flabébé`.
  Species names find their default form (`deoxys` shows *Deoxys Normal*).
- **List** all Pokémon page by page (`n` next, `p` previous, `q` quit), without
  downloading everything at once.
- **Details**: id, name, types, height (m), weight (kg), abilities (hidden ones
  marked) and the six base stats with a small bar chart.
- **Interactive menu** or **one-shot commands** (`pokedex search pikachu`).
- **Clear error messages, never a stack trace**: unknown Pokémon, invalid input,
  HTTP errors, API down, no internet, timeout and malformed responses.
- **In-memory cache**: going back to a page or Pokémon you already saw is instant.

## Requirements

- Python 3.13+
- Internet access (to reach the PokéAPI)

## Installation

```powershell
git clone https://github.com/BernardoOGomes/pokedex-cli.git
cd pokedex-cli
py -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e .            # optional: installs the "pokedex" command
```

## Usage

### Interactive menu

```powershell
python -m pokedex        # or just: pokedex
```

```text
=====================
POKEDEX
=====================

1. Search Pokémon
2. List Pokémon
3. Exit

Choose an option:
```

In the list view, type `n` (next page), `p` (previous page) or `q` (back to the
menu). `Ctrl+C` exits at any time.

### One-shot commands

```powershell
python -m pokedex search pikachu
python -m pokedex search 150
python -m pokedex list                     # page 1, 20 per page
python -m pokedex list --page 3 --limit 10
python -m pokedex --timeout 5 search mew   # wait at most 5 s for the API
python -m pokedex --help
```

Exit codes: `0` success, `1` expected error (e.g. Pokémon not found, API down),
`2` invalid command-line arguments, `130` interrupted with `Ctrl+C`.

## Project structure

```text
pokedex/
├── __main__.py         # "python -m pokedex" entry point
├── main.py             # argument parsing; wires the layers together
├── exceptions.py       # PokedexError hierarchy (one class per failure)
├── models/
│   └── pokemon.py      # Pokemon, Ability, Stat, PokemonSummary, PokemonPage
├── services/
│   └── pokeapi.py      # PokeApiClient: HTTP, status codes, JSON, cache
├── cli/
│   ├── menu.py         # PokedexApp: interactive menu and pagination
│   └── formatting.py   # pure functions: models -> text
└── utils/
    └── validation.py   # normalize and validate what the user types
tests/
├── fixtures/           # real PokeAPI responses saved as JSON
├── doubles.py          # fake HTTP responses and a fake data source
└── test_*.py           # one test module per application module
```

Each layer has a single responsibility and only depends on the layers below it:

```text
main.py ──> cli (menu, formatting) ──> services (PokeApiClient) ──> models
                     │                         │
                     └────────> exceptions <───┘
```

- **models** know nothing about HTTP or the terminal: they turn JSON into objects.
- **services** is the only place that knows about URLs, status codes and
  `requests`; every failure becomes a `PokeApiError`.
- **cli** is the only place that reads input and prints; it receives its data
  source, `input` and `print` as parameters, so it can be tested without a
  keyboard or the internet.

## Running the tests

```powershell
python -m pytest                    # unit tests (offline, ~2 s)
python -m pytest --cov              # with a coverage report (100%)
python -m pytest -m integration     # integration tests against the real API
```

The unit tests never touch the network: the HTTP session and the data source are
replaced by test doubles, and the sample responses in `tests/fixtures` are real
PokéAPI responses saved to disk.

## Code quality

```powershell
python -m ruff check .              # lint
python -m ruff format .             # format
python -m mypy                      # static type checking (strict mode)
```

All three, plus the tests, run automatically on every push through
[GitHub Actions](.github/workflows/ci.yml) on Ubuntu and Windows.

## Possible improvements

- Persistent cache on disk (e.g. `requests-cache` or SQLite) between runs.
- Automatic retries with backoff for temporary failures (HTTP 429/503).
- Search by type or ability, and show the evolution chain.
- A web API version with FastAPI reusing the same `models` and `services`.

## License

MIT. Pokémon data comes from [PokéAPI](https://pokeapi.co/); Pokémon is a
trademark of Nintendo, Game Freak and The Pokémon Company.
