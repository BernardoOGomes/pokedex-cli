"""Domain models: the Pokemon data the application actually uses.

The PokeAPI returns a lot more than we need (moves, sprites, game indices...).
These classes keep only the relevant fields and turn raw JSON dictionaries
into typed, immutable Python objects.

Parsing errors (a missing key, a wrong type) are raised as ``KeyError``,
``TypeError`` or ``ValueError``. The models do not know about HTTP: it is the
service layer's job to translate those into ``InvalidResponseError``.
"""

import math
from dataclasses import dataclass
from typing import Any, Self

# The PokeAPI measures height in decimetres and weight in hectograms.
DECIMETRES_PER_METRE = 10
HECTOGRAMS_PER_KILOGRAM = 10


@dataclass(frozen=True)
class Ability:
    name: str
    is_hidden: bool


@dataclass(frozen=True)
class Stat:
    name: str
    base_value: int


@dataclass(frozen=True)
class Pokemon:
    id: int
    name: str
    height: int  # decimetres, as returned by the API
    weight: int  # hectograms, as returned by the API
    types: tuple[str, ...]
    abilities: tuple[Ability, ...]
    stats: tuple[Stat, ...]

    @property
    def height_m(self) -> float:
        return self.height / DECIMETRES_PER_METRE

    @property
    def weight_kg(self) -> float:
        return self.weight / HECTOGRAMS_PER_KILOGRAM

    @property
    def total_stats(self) -> int:
        return sum(stat.base_value for stat in self.stats)

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> Self:
        """Build a Pokemon from the JSON of ``GET /pokemon/{name_or_id}``."""
        types = sorted(data["types"], key=lambda entry: entry["slot"])
        abilities = sorted(data["abilities"], key=lambda entry: entry["slot"])
        return cls(
            id=_as_int(data["id"]),
            name=_as_str(data["name"]),
            height=_as_int(data["height"]),
            weight=_as_int(data["weight"]),
            types=tuple(_as_str(entry["type"]["name"]) for entry in types),
            abilities=tuple(
                Ability(
                    name=_as_str(entry["ability"]["name"]),
                    is_hidden=bool(entry["is_hidden"]),
                )
                for entry in abilities
            ),
            stats=tuple(
                Stat(
                    name=_as_str(entry["stat"]["name"]),
                    base_value=_as_int(entry["base_stat"]),
                )
                for entry in data["stats"]
            ),
        )


@dataclass(frozen=True)
class PokemonSummary:
    """One item of a listing: just enough to show a name in a list."""

    id: int
    name: str

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> Self:
        """Build a summary from ``{"name": "...", "url": ".../pokemon/25/"}``."""
        return cls(id=_id_from_url(_as_str(data["url"])), name=_as_str(data["name"]))


@dataclass(frozen=True)
class PokemonPage:
    """One page of ``GET /pokemon?limit=...&offset=...``."""

    results: tuple[PokemonSummary, ...]
    total_count: int
    offset: int
    limit: int

    @property
    def first_position(self) -> int:
        """1-based position of the first item on this page."""
        return self.offset + 1

    @property
    def last_position(self) -> int:
        """1-based position of the last item on this page."""
        return self.offset + len(self.results)

    @property
    def page_number(self) -> int:
        """1-based number of this page (offset 0 -> page 1)."""
        return self.offset // self.limit + 1

    @property
    def page_count(self) -> int:
        """How many pages of this size exist in total (rounded up)."""
        return math.ceil(self.total_count / self.limit)

    @property
    def has_previous(self) -> bool:
        return self.offset > 0

    @property
    def has_next(self) -> bool:
        return self.offset + self.limit < self.total_count

    @classmethod
    def from_api_data(cls, data: dict[str, Any], offset: int, limit: int) -> Self:
        return cls(
            results=tuple(
                PokemonSummary.from_api_data(item) for item in data["results"]
            ),
            total_count=_as_int(data["count"]),
            offset=offset,
            limit=limit,
        )


def _id_from_url(url: str) -> int:
    """Extract the id from a resource URL such as ``.../pokemon/25/``."""
    return int(url.rstrip("/").rsplit("/", maxsplit=1)[-1])


def _as_int(value: Any) -> int:
    # bool is a subclass of int in Python, so it must be rejected explicitly.
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"expected an integer, got {value!r}")
    return value


def _as_str(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"expected a string, got {value!r}")
    return value
