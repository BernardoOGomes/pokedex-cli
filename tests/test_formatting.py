import pytest

from pokedex.cli.formatting import display_name, format_page, format_pokemon
from pokedex.models.pokemon import (
    Ability,
    Pokemon,
    PokemonPage,
    PokemonSummary,
    Stat,
)


@pytest.mark.parametrize(
    ("api_name", "expected"),
    [
        ("pikachu", "Pikachu"),
        ("mr-mime", "Mr Mime"),
        ("lightning-rod", "Lightning Rod"),
        ("special-attack", "Special Attack"),
    ],
)
def test_display_name(api_name: str, expected: str) -> None:
    assert display_name(api_name) == expected


class TestFormatPokemon:
    def test_full_output(self, pikachu: Pokemon) -> None:
        # A "snapshot" of the whole screen: any layout change shows up here.
        assert format_pokemon(pikachu) == (
            "========================================\n"
            "#0025  Pikachu\n"
            "========================================\n"
            "Types:     Electric\n"
            "Height:    0.4 m\n"
            "Weight:    6.0 kg\n"
            "Abilities: Static, Lightning Rod (hidden)\n"
            "\n"
            "Base stats\n"
            "  HP         35  ###\n"
            "  Attack     55  #####\n"
            "  Defense    40  ####\n"
            "  Sp. Atk    50  #####\n"
            "  Sp. Def    50  #####\n"
            "  Speed      90  #########\n"
            "  Total     320"
        )

    def test_shows_every_field_required_by_the_spec(self, pikachu: Pokemon) -> None:
        text = format_pokemon(pikachu)
        for expected in ["Pikachu", "25", "Electric", "m", "kg", "Static"]:
            assert expected in text
        for label in ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]:
            assert label in text

    def test_joins_two_types(self) -> None:
        pokemon = _pokemon(types=("grass", "poison"))
        assert "Types:     Grass / Poison" in format_pokemon(pokemon)

    def test_unknown_stat_uses_its_api_name(self) -> None:
        pokemon = _pokemon(stats=(Stat("accuracy", 100),))
        assert "  Accuracy  100  ##########" in format_pokemon(pokemon)

    def test_very_low_stat_still_shows_one_bar(self) -> None:
        pokemon = _pokemon(stats=(Stat("hp", 1),))
        assert "  HP          1  #\n" in format_pokemon(pokemon)

    def test_converts_units(self) -> None:
        pokemon = _pokemon(height=17, weight=905)  # Charizard
        text = format_pokemon(pokemon)
        assert "Height:    1.7 m" in text
        assert "Weight:    90.5 kg" in text


class TestFormatPage:
    def test_header_and_numbered_names(self) -> None:
        page = PokemonPage(
            results=(
                PokemonSummary(1, "bulbasaur"),
                PokemonSummary(2, "ivysaur"),
                PokemonSummary(3, "venusaur"),
            ),
            total_count=1351,
            offset=0,
            limit=3,
        )
        assert format_page(page) == (
            "Showing Pokémon 1-3 of 1351 (page 1/451)\n"
            "\n"
            "1. Bulbasaur\n"
            "2. Ivysaur\n"
            "3. Venusaur"
        )

    def test_numbers_are_right_aligned(self) -> None:
        page = PokemonPage(
            results=(PokemonSummary(99, "a"), PokemonSummary(100, "b")),
            total_count=200,
            offset=98,
            limit=2,
        )
        assert format_page(page).splitlines()[2:] == [" 99. A", "100. B"]

    def test_empty_page(self) -> None:
        page = PokemonPage(results=(), total_count=10, offset=100, limit=20)
        assert format_page(page) == "No Pokémon on this page (the last page is 1)."


def _pokemon(
    types: tuple[str, ...] = ("normal",),
    stats: tuple[Stat, ...] = (Stat("hp", 50),),
    height: int = 10,
    weight: int = 100,
) -> Pokemon:
    return Pokemon(
        id=1,
        name="testmon",
        height=height,
        weight=weight,
        types=types,
        abilities=(Ability("run-away", is_hidden=False),),
        stats=stats,
    )
