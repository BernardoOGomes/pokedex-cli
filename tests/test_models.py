import dataclasses
from typing import Any

import pytest

from pokedex.models.pokemon import (
    Ability,
    Pokemon,
    PokemonPage,
    PokemonSummary,
    Stat,
)


class TestPokemonFromApiData:
    def test_reads_basic_fields(self, pikachu: Pokemon) -> None:
        assert pikachu.id == 25
        assert pikachu.name == "pikachu"
        assert pikachu.height == 4
        assert pikachu.weight == 60

    def test_reads_types(self, pikachu: Pokemon) -> None:
        assert pikachu.types == ("electric",)

    def test_reads_abilities_with_hidden_flag(self, pikachu: Pokemon) -> None:
        assert pikachu.abilities == (
            Ability(name="static", is_hidden=False),
            Ability(name="lightning-rod", is_hidden=True),
        )

    def test_reads_the_six_stats_in_api_order(self, pikachu: Pokemon) -> None:
        assert pikachu.stats == (
            Stat("hp", 35),
            Stat("attack", 55),
            Stat("defense", 40),
            Stat("special-attack", 50),
            Stat("special-defense", 50),
            Stat("speed", 90),
        )

    def test_keeps_only_relevant_fields(self, pikachu_data: dict[str, Any]) -> None:
        assert "base_experience" in pikachu_data  # present in the JSON...
        fields = {field.name for field in dataclasses.fields(Pokemon)}
        assert fields == {
            "id",
            "name",
            "height",
            "weight",
            "types",
            "abilities",
            "stats",
        }  # ...but not in the model

    def test_orders_types_by_slot(self, bulbasaur_data: dict[str, Any]) -> None:
        bulbasaur_data["types"].reverse()  # API order must not matter
        bulbasaur = Pokemon.from_api_data(bulbasaur_data)
        assert bulbasaur.types == ("grass", "poison")

    def test_orders_abilities_by_slot(self, bulbasaur_data: dict[str, Any]) -> None:
        bulbasaur_data["abilities"].reverse()
        bulbasaur = Pokemon.from_api_data(bulbasaur_data)
        assert [a.name for a in bulbasaur.abilities] == ["overgrow", "chlorophyll"]

    @pytest.mark.parametrize(
        "missing_key", ["id", "name", "height", "weight", "types", "stats"]
    )
    def test_missing_key_raises_key_error(
        self, pikachu_data: dict[str, Any], missing_key: str
    ) -> None:
        del pikachu_data[missing_key]
        with pytest.raises(KeyError):
            Pokemon.from_api_data(pikachu_data)

    @pytest.mark.parametrize(
        ("key", "bad_value"),
        [("id", "25"), ("id", True), ("height", 4.5), ("name", 25), ("name", None)],
    )
    def test_wrong_type_raises_type_error(
        self, pikachu_data: dict[str, Any], key: str, bad_value: Any
    ) -> None:
        pikachu_data[key] = bad_value
        with pytest.raises(TypeError):
            Pokemon.from_api_data(pikachu_data)

    def test_wrong_nested_type_raises_type_error(
        self, pikachu_data: dict[str, Any]
    ) -> None:
        pikachu_data["stats"][0]["base_stat"] = "35"
        with pytest.raises(TypeError):
            Pokemon.from_api_data(pikachu_data)


class TestPokemonProperties:
    def test_height_in_metres(self, pikachu: Pokemon) -> None:
        assert pikachu.height_m == pytest.approx(0.4)

    def test_weight_in_kilograms(self, pikachu: Pokemon) -> None:
        assert pikachu.weight_kg == pytest.approx(6.0)

    def test_total_stats(self, pikachu: Pokemon) -> None:
        assert pikachu.total_stats == 320

    def test_is_immutable(self, pikachu: Pokemon) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            pikachu.name = "raichu"  # type: ignore[misc]


class TestPokemonSummary:
    @pytest.mark.parametrize(
        "url",
        [
            "https://pokeapi.co/api/v2/pokemon/25/",
            "https://pokeapi.co/api/v2/pokemon/25",
        ],
    )
    def test_reads_id_from_url(self, url: str) -> None:
        summary = PokemonSummary.from_api_data({"name": "pikachu", "url": url})
        assert summary == PokemonSummary(id=25, name="pikachu")

    def test_url_without_number_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="invalid literal"):
            PokemonSummary.from_api_data(
                {"name": "pikachu", "url": "https://pokeapi.co/api/v2/pokemon/"}
            )


class TestPokemonPage:
    def test_reads_results_and_count(self, list_data: dict[str, Any]) -> None:
        page = PokemonPage.from_api_data(list_data, offset=0, limit=20)
        assert len(page.results) == 20
        assert page.results[0] == PokemonSummary(id=1, name="bulbasaur")
        assert page.results[2] == PokemonSummary(id=3, name="venusaur")
        assert page.total_count == list_data["count"]

    def test_positions_are_one_based(self) -> None:
        page = _page(offset=20, limit=20, size=20, total=100)
        assert (page.first_position, page.last_position) == (21, 40)

    def test_last_page_may_be_partial(self) -> None:
        page = _page(offset=40, limit=20, size=5, total=45)
        assert (page.first_position, page.last_position) == (41, 45)

    @pytest.mark.parametrize(
        ("offset", "has_previous", "has_next"),
        [(0, False, True), (20, True, True), (40, True, False)],
    )
    def test_navigation_flags(
        self, offset: int, has_previous: bool, has_next: bool
    ) -> None:
        page = _page(offset=offset, limit=20, size=5, total=45)
        assert page.has_previous is has_previous
        assert page.has_next is has_next

    @pytest.mark.parametrize(
        ("offset", "limit", "total", "page_number", "page_count"),
        [
            (0, 20, 1351, 1, 68),
            (20, 20, 1351, 2, 68),
            (1340, 20, 1351, 68, 68),
            (0, 20, 40, 1, 2),  # exact multiple: no extra empty page
            (0, 20, 5, 1, 1),
        ],
    )
    def test_page_number_and_count(
        self, offset: int, limit: int, total: int, page_number: int, page_count: int
    ) -> None:
        page = _page(offset=offset, limit=limit, size=1, total=total)
        assert page.page_number == page_number
        assert page.page_count == page_count

    def test_exact_multiple_has_no_next_page(self) -> None:
        page = _page(offset=20, limit=20, size=20, total=40)
        assert page.has_next is False


def _page(offset: int, limit: int, size: int, total: int) -> PokemonPage:
    results = tuple(
        PokemonSummary(id=n, name=f"pokemon-{n}")
        for n in range(offset + 1, offset + size + 1)
    )
    return PokemonPage(results=results, total_count=total, offset=offset, limit=limit)
