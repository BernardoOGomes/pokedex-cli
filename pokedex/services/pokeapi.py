"""HTTP client for the PokeAPI (https://pokeapi.co).

This is the only module that knows about URLs, HTTP status codes and the
``requests`` library. Everything it returns is a domain object from
``pokedex.models``; everything that goes wrong becomes a ``PokeApiError``.
"""

from typing import Any, Self

import requests

from pokedex import __version__
from pokedex.exceptions import (
    ApiHttpError,
    ApiTimeoutError,
    ApiUnavailableError,
    InvalidResponseError,
    PokemonNotFoundError,
)
from pokedex.models.pokemon import Pokemon, PokemonPage
from pokedex.utils.validation import API_NAME_PATTERN, normalize_query

DEFAULT_BASE_URL = "https://pokeapi.co/api/v2"
DEFAULT_TIMEOUT = 10.0  # seconds
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Exceptions raised by the model parsers when the JSON has an unexpected shape.
_PARSING_ERRORS = (KeyError, TypeError, ValueError, AttributeError)


class PokeApiClient:
    """Fetches Pokemon from the PokeAPI and converts them into models.

    The ``requests.Session`` is injected so tests can pass a fake one and
    run without internet. A session also reuses the TCP connection between
    requests, which makes paging through the list faster.

    Responses are cached in memory for the lifetime of the client: going
    back to a page you already saw costs no request, and the PokeAPI's fair
    use policy asks clients to cache what they download.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._session = session if session is not None else requests.Session()
        self._session.headers.update({"User-Agent": f"pokedex-cli/{__version__}"})
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._pokemon_cache: dict[str, Pokemon] = {}
        self._page_cache: dict[tuple[int, int], PokemonPage] = {}

    def close(self) -> None:
        """Close the underlying HTTP connections."""
        self._session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def get_pokemon(self, name_or_id: str | int) -> Pokemon:
        """Return one Pokemon by name (``"pikachu"``) or number (``25``)."""
        query = normalize_query(str(name_or_id))
        if query in self._pokemon_cache:
            return self._pokemon_cache[query]

        try:
            data = self._get_json(f"pokemon/{query}", not_found_query=query)
        except PokemonNotFoundError:
            if query.isdigit():
                raise
            # "deoxys" is a 404, but its species knows the default form,
            # "deoxys-normal". One extra request, only when the first misses.
            form_name = self._default_form_name(query)
            data = self._get_json(f"pokemon/{form_name}", not_found_query=query)

        try:
            pokemon = Pokemon.from_api_data(data)
        except _PARSING_ERRORS as error:
            raise InvalidResponseError() from error

        # Cache under every key, so "pikachu" and "25" share one entry.
        for key in (query, pokemon.name, str(pokemon.id)):
            self._pokemon_cache[key] = pokemon
        return pokemon

    def list_pokemon(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
    ) -> PokemonPage:
        """Return one page of the Pokemon list, without loading all of them."""
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        if offset < 0:
            raise ValueError("offset must not be negative")

        key = (limit, offset)
        if key in self._page_cache:
            return self._page_cache[key]

        data = self._get_json("pokemon", params={"limit": limit, "offset": offset})
        try:
            page = PokemonPage.from_api_data(data, offset=offset, limit=limit)
        except _PARSING_ERRORS as error:
            raise InvalidResponseError() from error

        self._page_cache[key] = page
        return page

    def _default_form_name(self, species_name: str) -> str:
        """Return the name of a species' default form, e.g. "deoxys-normal"."""
        data = self._get_json(
            f"pokemon-species/{species_name}", not_found_query=species_name
        )
        try:
            for variety in data["varieties"]:
                if variety["is_default"]:
                    return _as_api_name(variety["pokemon"]["name"])
        except _PARSING_ERRORS as error:
            raise InvalidResponseError() from error
        raise InvalidResponseError()  # a species without a default form

    def _get_json(
        self,
        path: str,
        params: dict[str, int] | None = None,
        not_found_query: str | None = None,
    ) -> dict[str, Any]:
        """GET ``base_url/path`` and return the decoded JSON object.

        Translates every ``requests`` failure into a ``PokeApiError`` so the
        rest of the application never has to import ``requests``.
        """
        url = f"{self._base_url}/{path}"
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
        except requests.Timeout as error:
            raise ApiTimeoutError(self._timeout) from error
        except requests.RequestException as error:
            # ConnectionError, TooManyRedirects, invalid URL, ...
            raise ApiUnavailableError() from error

        status = response.status_code
        if status == 404 and not_found_query is not None:
            raise PokemonNotFoundError(not_found_query)
        if status >= 500:
            raise ApiUnavailableError()
        if status != 200:
            raise ApiHttpError(status)

        try:
            data = response.json()
        except ValueError as error:  # requests' JSONDecodeError is a ValueError
            raise InvalidResponseError() from error
        if not isinstance(data, dict):
            raise InvalidResponseError()
        return data


def _as_api_name(value: Any) -> str:
    """Check a name that came from the API before putting it in a URL."""
    if not isinstance(value, str) or not API_NAME_PATTERN.fullmatch(value):
        raise ValueError(f"not a valid Pokemon name: {value!r}")
    return value
