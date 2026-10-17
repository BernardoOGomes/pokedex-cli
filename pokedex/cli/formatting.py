"""Pure functions that turn models into text for the terminal.

Nothing here reads input, prints or touches the network: each function takes
data and returns a string. That makes the presentation trivial to test.
"""

from pokedex.models.pokemon import Pokemon, PokemonPage

SEPARATOR_WIDTH = 40

STAT_LABELS = {
    "hp": "HP",
    "attack": "Attack",
    "defense": "Defense",
    "special-attack": "Sp. Atk",
    "special-defense": "Sp. Def",
    "speed": "Speed",
}

# One "#" per 10 points; the highest base stat in the games is 255.
STAT_POINTS_PER_BAR_CHAR = 10


def display_name(api_name: str) -> str:
    """``"mr-mime"`` -> ``"Mr Mime"``, ``"pikachu"`` -> ``"Pikachu"``."""
    return api_name.replace("-", " ").title()


def format_pokemon(pokemon: Pokemon) -> str:
    """Return the full details screen of a Pokemon."""
    abilities = ", ".join(
        display_name(ability.name) + (" (hidden)" if ability.is_hidden else "")
        for ability in pokemon.abilities
    )
    lines = [
        "=" * SEPARATOR_WIDTH,
        f"#{pokemon.id:04d}  {display_name(pokemon.name)}",
        "=" * SEPARATOR_WIDTH,
        f"{'Types:':<11}{' / '.join(display_name(t) for t in pokemon.types)}",
        f"{'Height:':<11}{pokemon.height_m:.1f} m",
        f"{'Weight:':<11}{pokemon.weight_kg:.1f} kg",
        f"{'Abilities:':<11}{abilities}",
        "",
        "Base stats",
    ]
    for stat in pokemon.stats:
        label = STAT_LABELS.get(stat.name, display_name(stat.name))
        bar = "#" * max(1, stat.base_value // STAT_POINTS_PER_BAR_CHAR)
        lines.append(f"  {label:<9}{stat.base_value:>4}  {bar}")
    lines.append(f"  {'Total':<9}{pokemon.total_stats:>4}")
    return "\n".join(lines)


def format_page(page: PokemonPage) -> str:
    """Return one page of the Pokemon list, numbered by position."""
    if not page.results:
        return f"No Pokémon on this page (the last page is {page.page_count})."

    lines = [
        f"Showing Pokémon {page.first_position}-{page.last_position} "
        f"of {page.total_count} (page {page.page_number}/{page.page_count})",
        "",
    ]
    number_width = len(str(page.last_position))
    for position, summary in enumerate(page.results, start=page.first_position):
        lines.append(f"{position:>{number_width}}. {display_name(summary.name)}")
    return "\n".join(lines)
