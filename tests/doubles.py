"""Test doubles: fake objects that replace the network and the PokeAPI."""

from typing import Any
from unittest.mock import Mock

import requests

from pokedex.exceptions import PokemonNotFoundError
from pokedex.models.pokemon import Pokemon, PokemonPage, PokemonSummary


def make_response(
    status_code: int = 200, json_data: Any = None, invalid_json: bool = False
) -> Mock:
    """Build a fake ``requests.Response`` with the given status and body."""
    response = Mock(spec=requests.Response)
    response.status_code = status_code
    if invalid_json:
        response.json.side_effect = requests.exceptions.JSONDecodeError(
            "Expecting value", "<html>", 0
        )
    else:
        response.json.return_value = json_data
    return response


class FakeSource:
    """In-memory stand-in for ``PokeApiClient``, used by the CLI tests.

    It holds ``total`` numbered Pokemon ("pokemon-1", "pokemon-2", ...) and
    can simulate failures: ``error`` is raised by every call while it is set,
    and ``page_errors[offset]`` is raised once, the next time that page loads.
    """

    def __init__(self, pokemon: list[Pokemon], total: int = 45) -> None:
        self._by_key = {p.name: p for p in pokemon} | {str(p.id): p for p in pokemon}
        self.total = total
        self.error: Exception | None = None
        self.page_errors: dict[int, Exception] = {}
        self.list_calls: list[tuple[int, int]] = []

    def get_pokemon(self, name_or_id: str | int) -> Pokemon:
        if self.error is not None:
            raise self.error
        key = str(name_or_id).strip().lower()
        if key not in self._by_key:
            raise PokemonNotFoundError(key)
        return self._by_key[key]

    def list_pokemon(self, limit: int = 20, offset: int = 0) -> PokemonPage:
        self.list_calls.append((limit, offset))
        if self.error is not None:
            raise self.error
        if offset in self.page_errors:
            raise self.page_errors.pop(offset)
        numbers = range(offset + 1, min(offset + limit, self.total) + 1)
        return PokemonPage(
            results=tuple(PokemonSummary(id=n, name=f"pokemon-{n}") for n in numbers),
            total_count=self.total,
            offset=offset,
            limit=limit,
        )
