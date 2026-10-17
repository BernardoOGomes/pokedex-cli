"""Exception hierarchy for the Pokedex application.

Every expected failure is represented by a subclass of ``PokedexError``.
The CLI catches ``PokedexError`` and prints ``str(error)``, so each message
is written for the end user and never shows a stack trace.

    PokedexError
    ├── InvalidInputError
    └── PokeApiError
        ├── PokemonNotFoundError
        ├── ApiUnavailableError
        ├── ApiTimeoutError
        ├── ApiHttpError
        └── InvalidResponseError
"""


class PokedexError(Exception):
    """Base class for every expected error in the application."""


class InvalidInputError(PokedexError):
    """The user typed something that is not a valid Pokemon name or number."""


class PokeApiError(PokedexError):
    """Base class for errors that happen while talking to the PokeAPI."""


class PokemonNotFoundError(PokeApiError):
    """The PokeAPI answered 404: no Pokemon matches the query."""

    def __init__(self, query: str) -> None:
        super().__init__("Pokémon not found.")
        self.query = query


class ApiUnavailableError(PokeApiError):
    """The PokeAPI could not be reached (no connection or a 5xx response)."""

    def __init__(
        self,
        message: str = (
            "The PokéAPI is unavailable right now. "
            "Check your internet connection and try again."
        ),
    ) -> None:
        super().__init__(message)


class ApiTimeoutError(PokeApiError):
    """The PokeAPI took longer than the configured timeout to answer."""

    def __init__(self, timeout: float) -> None:
        super().__init__(
            f"The PokéAPI took too long to respond (more than {timeout:g}s). "
            "Please try again."
        )
        self.timeout = timeout


class ApiHttpError(PokeApiError):
    """The PokeAPI answered with an unexpected HTTP status (e.g. 400, 429)."""

    def __init__(self, status_code: int) -> None:
        super().__init__(
            f"The PokéAPI returned an unexpected error (HTTP {status_code})."
        )
        self.status_code = status_code


class InvalidResponseError(PokeApiError):
    """The PokeAPI answered, but the body is not the JSON we expected."""

    def __init__(
        self, message: str = "The PokéAPI sent an unexpected response."
    ) -> None:
        super().__init__(message)
