import pytest

from pokedex.exceptions import InvalidInputError
from pokedex.utils.validation import normalize_query


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pikachu", "pikachu"),
        ("  Pikachu  ", "pikachu"),
        ("PIKACHU", "pikachu"),
        ("25", "25"),
        ("025", "25"),  # the API answers 404 for "025"
        (" 7 ", "7"),
        ("mr-mime", "mr-mime"),
        ("Mr. Mime", "mr-mime"),
        ("tapu   koko", "tapu-koko"),
        ("Farfetch'd", "farfetchd"),
        ("porygon-z", "porygon-z"),
        ("porygon2", "porygon2"),
        ("Flabébé", "flabebe"),
    ],
)
def test_normalizes_valid_input(raw: str, expected: str) -> None:
    assert normalize_query(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_rejects_empty_input(raw: str) -> None:
    with pytest.raises(InvalidInputError, match="Please enter"):
        normalize_query(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "pika@chu",
        "pikachu!",
        "../pokemon",
        "pika/chu",
        "-pikachu",
        "a--b",
        "ピカチュウ",
    ],
)
def test_rejects_invalid_characters(raw: str) -> None:
    with pytest.raises(InvalidInputError, match="Invalid input"):
        normalize_query(raw)


@pytest.mark.parametrize("raw", ["0", "000"])
def test_rejects_zero(raw: str) -> None:
    with pytest.raises(InvalidInputError, match="start at 1"):
        normalize_query(raw)


def test_negative_number_is_invalid() -> None:
    with pytest.raises(InvalidInputError):
        normalize_query("-5")
