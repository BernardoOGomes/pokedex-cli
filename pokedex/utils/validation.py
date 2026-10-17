"""Validation and normalization of what the user types."""

import re
import unicodedata

from pokedex.exceptions import InvalidInputError

# PokeAPI names are lowercase words joined by single hyphens: "mr-mime", "porygon-z".
API_NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def normalize_query(raw: str) -> str:
    """Turn user input into the form the PokeAPI expects.

    Examples: ``" Pikachu "`` -> ``"pikachu"``, ``"Mr. Mime"`` -> ``"mr-mime"``,
    ``"025"`` -> ``"25"``. Raises ``InvalidInputError`` for input that can
    never match a Pokemon, so we do not waste an HTTP request on it.
    """
    query = raw.strip().lower()
    if not query:
        raise InvalidInputError("Please enter a Pokémon name or number.")

    # Accept the way people usually write names: "mr. mime", "tapu koko",
    # "flabébé" (the API uses plain ASCII: "flabebe").
    query = _strip_accents(query)
    query = query.replace(".", "").replace("'", "")
    query = re.sub(r"\s+", "-", query)

    if not API_NAME_PATTERN.fullmatch(query):
        raise InvalidInputError(
            "Invalid input: use only letters, numbers, spaces and hyphens."
        )

    if query.isdigit():
        number = int(query)  # also removes leading zeros: "025" -> 25
        if number < 1:
            raise InvalidInputError("Pokémon numbers start at 1.")
        return str(number)

    return query


def _strip_accents(text: str) -> str:
    """``"flabébé"`` -> ``"flabebe"``.

    NFKD splits "é" into "e" + a combining accent mark; ``combining`` tells
    us which characters are those marks, so we can drop them.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))
