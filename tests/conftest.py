"""Shared pytest fixtures (pytest loads this file automatically).

The JSON files in ``tests/fixtures`` are real PokeAPI responses, trimmed to
the fields the app uses (plus ``base_experience``, to prove that extra fields
are ignored). Loading them from disk keeps the tests fast and offline.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from pokedex.models.pokemon import Pokemon
from tests.doubles import FakeSource

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURES_DIR / name).open(encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data


@pytest.fixture
def pikachu_data() -> dict[str, Any]:
    return load_fixture("pikachu.json")


@pytest.fixture
def bulbasaur_data() -> dict[str, Any]:
    return load_fixture("bulbasaur.json")


@pytest.fixture
def deoxys_species_data() -> dict[str, Any]:
    return load_fixture("deoxys_species.json")


@pytest.fixture
def deoxys_normal_data() -> dict[str, Any]:
    return load_fixture("deoxys_normal.json")


@pytest.fixture
def list_data() -> dict[str, Any]:
    return load_fixture("pokemon_list.json")


@pytest.fixture
def pikachu(pikachu_data: dict[str, Any]) -> Pokemon:
    return Pokemon.from_api_data(pikachu_data)


@pytest.fixture
def fake_source(pikachu: Pokemon) -> FakeSource:
    return FakeSource([pikachu])
