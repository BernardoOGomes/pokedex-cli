"""Integration tests: talk to the REAL PokeAPI over the internet.

They are skipped by default (see ``addopts`` in pyproject.toml), because a
unit test suite must be fast and must not fail when the network is down.
Run them on purpose with:

    pytest -m integration
"""

import pytest

from pokedex.exceptions import PokemonNotFoundError
from pokedex.services.pokeapi import PokeApiClient

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> PokeApiClient:
    return PokeApiClient()


def test_get_pikachu_by_name(client: PokeApiClient) -> None:
    pokemon = client.get_pokemon("pikachu")
    assert pokemon.id == 25
    assert pokemon.types == ("electric",)
    assert len(pokemon.stats) == 6


def test_get_by_number_with_leading_zero(client: PokeApiClient) -> None:
    assert client.get_pokemon("001").name == "bulbasaur"


def test_species_name_finds_default_form(client: PokeApiClient) -> None:
    pokemon = client.get_pokemon("Deoxys")
    assert (pokemon.id, pokemon.name) == (386, "deoxys-normal")


def test_unknown_pokemon(client: PokeApiClient) -> None:
    with pytest.raises(PokemonNotFoundError):
        client.get_pokemon("abc123")


def test_first_page(client: PokeApiClient) -> None:
    page = client.list_pokemon(limit=20, offset=0)
    assert [p.name for p in page.results[:3]] == ["bulbasaur", "ivysaur", "venusaur"]
    assert page.total_count > 1000
    assert page.has_next
    assert not page.has_previous
