"""Tests for PokeApiClient. No test here touches the network.

A real ``requests.Session`` is created, but its ``get`` method is replaced by
a ``Mock`` that returns fake responses (or raises ``requests`` exceptions).
"""

from typing import Any
from unittest.mock import Mock

import pytest
import requests

from pokedex.exceptions import (
    ApiHttpError,
    ApiTimeoutError,
    ApiUnavailableError,
    InvalidInputError,
    InvalidResponseError,
    PokeApiError,
    PokemonNotFoundError,
)
from pokedex.services.pokeapi import DEFAULT_BASE_URL, PokeApiClient
from tests.doubles import make_response


@pytest.fixture
def session() -> requests.Session:
    session = requests.Session()
    session.get = Mock(name="get")  # type: ignore[method-assign]
    return session


@pytest.fixture
def get(session: requests.Session) -> Mock:
    """The fake ``session.get``, to configure answers and inspect calls."""
    mock: Mock = session.get  # type: ignore[assignment]
    return mock


@pytest.fixture
def client(session: requests.Session) -> PokeApiClient:
    return PokeApiClient(session=session, timeout=5)


class TestGetPokemon:
    def test_returns_a_pokemon(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=pikachu_data)

        pokemon = client.get_pokemon("pikachu")

        assert pokemon.id == 25
        assert pokemon.name == "pikachu"

    def test_calls_the_right_url_with_timeout(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=pikachu_data)

        client.get_pokemon(25)

        get.assert_called_once_with(
            f"{DEFAULT_BASE_URL}/pokemon/25", params=None, timeout=5
        )

    def test_normalizes_the_query_before_the_request(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=pikachu_data)

        client.get_pokemon("  PIKACHU ")

        assert get.call_args.args[0].endswith("/pokemon/pikachu")

    def test_invalid_input_never_reaches_the_api(
        self, client: PokeApiClient, get: Mock
    ) -> None:
        with pytest.raises(InvalidInputError):
            client.get_pokemon("pika@chu")
        get.assert_not_called()

    def test_404_raises_not_found(self, client: PokeApiClient, get: Mock) -> None:
        get.return_value = make_response(404, json_data={"message": "Not Found"})

        with pytest.raises(
            PokemonNotFoundError, match=r"^Pokémon not found\.$"
        ) as info:
            client.get_pokemon("abc123")

        assert info.value.query == "abc123"


class TestSpeciesFallback:
    """Some Pokemon only exist in /pokemon under a form name.

    ``/pokemon/deoxys`` is a 404 because the default form is called
    "deoxys-normal". The species endpoint tells us which form is the default.
    """

    def test_finds_the_default_form_by_species_name(
        self,
        client: PokeApiClient,
        get: Mock,
        deoxys_species_data: dict[str, Any],
        deoxys_normal_data: dict[str, Any],
    ) -> None:
        get.side_effect = [
            make_response(404),
            make_response(json_data=deoxys_species_data),
            make_response(json_data=deoxys_normal_data),
        ]

        pokemon = client.get_pokemon("deoxys")

        assert (pokemon.id, pokemon.name) == (386, "deoxys-normal")
        urls = [call.args[0] for call in get.call_args_list]
        assert urls == [
            f"{DEFAULT_BASE_URL}/pokemon/deoxys",
            f"{DEFAULT_BASE_URL}/pokemon-species/deoxys",
            f"{DEFAULT_BASE_URL}/pokemon/deoxys-normal",
        ]

    def test_species_name_is_cached(
        self,
        client: PokeApiClient,
        get: Mock,
        deoxys_species_data: dict[str, Any],
        deoxys_normal_data: dict[str, Any],
    ) -> None:
        get.side_effect = [
            make_response(404),
            make_response(json_data=deoxys_species_data),
            make_response(json_data=deoxys_normal_data),
        ]

        client.get_pokemon("deoxys")
        client.get_pokemon("deoxys")
        client.get_pokemon(386)

        assert get.call_count == 3  # only the first search hit the API

    def test_unknown_species_is_not_found(
        self, client: PokeApiClient, get: Mock
    ) -> None:
        get.return_value = make_response(404)

        with pytest.raises(PokemonNotFoundError) as info:
            client.get_pokemon("abc123")

        assert info.value.query == "abc123"
        assert get.call_count == 2  # /pokemon and /pokemon-species

    def test_numbers_do_not_use_the_fallback(
        self, client: PokeApiClient, get: Mock
    ) -> None:
        get.return_value = make_response(404)

        with pytest.raises(PokemonNotFoundError):
            client.get_pokemon(99999)

        get.assert_called_once()

    @pytest.mark.parametrize(
        "species_body",
        [
            {"varieties": []},  # no default form
            {"varieties": [{"is_default": False, "pokemon": {"name": "x"}}]},
            {"no_varieties": True},
            # a name that would change the URL must never be requested
            {"varieties": [{"is_default": True, "pokemon": {"name": "../admin"}}]},
        ],
    )
    def test_malformed_species_is_an_invalid_response(
        self, client: PokeApiClient, get: Mock, species_body: dict[str, Any]
    ) -> None:
        get.side_effect = [make_response(404), make_response(json_data=species_body)]

        with pytest.raises(InvalidResponseError):
            client.get_pokemon("deoxys")


class TestHttpErrors:
    """Every failure becomes a PokeApiError with a clear message."""

    @pytest.mark.parametrize("status", [500, 502, 503, 504])
    def test_5xx_means_api_unavailable(
        self, client: PokeApiClient, get: Mock, status: int
    ) -> None:
        get.return_value = make_response(status)
        with pytest.raises(ApiUnavailableError, match="unavailable"):
            client.get_pokemon("pikachu")

    @pytest.mark.parametrize("status", [400, 403, 429, 301])
    def test_other_statuses_raise_http_error(
        self, client: PokeApiClient, get: Mock, status: int
    ) -> None:
        get.return_value = make_response(status)
        with pytest.raises(ApiHttpError, match=f"HTTP {status}") as info:
            client.get_pokemon("pikachu")
        assert info.value.status_code == status

    def test_timeout(self, client: PokeApiClient, get: Mock) -> None:
        get.side_effect = requests.Timeout("read timed out")
        with pytest.raises(ApiTimeoutError, match="more than 5s") as info:
            client.get_pokemon("pikachu")
        assert info.value.timeout == 5

    def test_connect_timeout_is_also_a_timeout(
        self, client: PokeApiClient, get: Mock
    ) -> None:
        get.side_effect = requests.ConnectTimeout("connect timed out")
        with pytest.raises(ApiTimeoutError):
            client.get_pokemon("pikachu")

    def test_no_connection(self, client: PokeApiClient, get: Mock) -> None:
        get.side_effect = requests.ConnectionError("Name or service not known")
        with pytest.raises(ApiUnavailableError, match="internet connection"):
            client.get_pokemon("pikachu")

    def test_any_other_requests_error(self, client: PokeApiClient, get: Mock) -> None:
        get.side_effect = requests.TooManyRedirects("loop")
        with pytest.raises(ApiUnavailableError):
            client.get_pokemon("pikachu")

    def test_keeps_the_original_exception_as_cause(
        self, client: PokeApiClient, get: Mock
    ) -> None:
        original = requests.ConnectionError("boom")
        get.side_effect = original
        with pytest.raises(ApiUnavailableError) as info:
            client.get_pokemon("pikachu")
        assert info.value.__cause__ is original  # useful when debugging


class TestInvalidResponses:
    def test_body_is_not_json(self, client: PokeApiClient, get: Mock) -> None:
        get.return_value = make_response(invalid_json=True)
        with pytest.raises(InvalidResponseError, match="unexpected response"):
            client.get_pokemon("pikachu")

    @pytest.mark.parametrize("body", [[], [1, 2], "text", 42, None])
    def test_json_is_not_an_object(
        self, client: PokeApiClient, get: Mock, body: Any
    ) -> None:
        get.return_value = make_response(json_data=body)
        with pytest.raises(InvalidResponseError):
            client.get_pokemon("pikachu")

    def test_object_with_missing_fields(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        del pikachu_data["stats"]
        get.return_value = make_response(json_data=pikachu_data)
        with pytest.raises(InvalidResponseError) as info:
            client.get_pokemon("pikachu")
        assert isinstance(info.value.__cause__, KeyError)

    def test_object_with_wrong_types(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        pikachu_data["types"] = "electric"  # should be a list of objects
        get.return_value = make_response(json_data=pikachu_data)
        with pytest.raises(InvalidResponseError):
            client.get_pokemon("pikachu")

    def test_list_with_missing_fields(self, client: PokeApiClient, get: Mock) -> None:
        get.return_value = make_response(json_data={"results": []})  # no "count"
        with pytest.raises(InvalidResponseError):
            client.list_pokemon()

    def test_all_errors_share_one_base_class(
        self, client: PokeApiClient, get: Mock
    ) -> None:
        get.return_value = make_response(invalid_json=True)
        with pytest.raises(PokeApiError):
            client.get_pokemon("pikachu")


class TestListPokemon:
    def test_returns_a_page(
        self, client: PokeApiClient, get: Mock, list_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=list_data)

        page = client.list_pokemon(limit=20, offset=0)

        assert page.results[0].name == "bulbasaur"
        assert (page.offset, page.limit) == (0, 20)
        assert page.total_count == list_data["count"]

    def test_sends_limit_and_offset_as_query_params(
        self, client: PokeApiClient, get: Mock, list_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=list_data)

        client.list_pokemon(limit=20, offset=40)

        get.assert_called_once_with(
            f"{DEFAULT_BASE_URL}/pokemon",
            params={"limit": 20, "offset": 40},
            timeout=5,
        )

    def test_404_on_the_list_is_not_a_missing_pokemon(
        self, client: PokeApiClient, get: Mock
    ) -> None:
        get.return_value = make_response(404)
        with pytest.raises(ApiHttpError):
            client.list_pokemon()

    @pytest.mark.parametrize("limit", [0, -1, 101])
    def test_rejects_invalid_limit(self, client: PokeApiClient, limit: int) -> None:
        with pytest.raises(ValueError, match="limit"):
            client.list_pokemon(limit=limit)

    def test_rejects_negative_offset(self, client: PokeApiClient) -> None:
        with pytest.raises(ValueError, match="offset"):
            client.list_pokemon(offset=-20)


class TestCache:
    def test_same_pokemon_twice_makes_one_request(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=pikachu_data)

        first = client.get_pokemon("pikachu")
        second = client.get_pokemon("pikachu")

        assert first is second
        assert get.call_count == 1

    def test_name_and_number_share_the_cache(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=pikachu_data)

        client.get_pokemon("pikachu")
        client.get_pokemon(25)
        client.get_pokemon("025")

        assert get.call_count == 1

    def test_errors_are_not_cached(
        self, client: PokeApiClient, get: Mock, pikachu_data: dict[str, Any]
    ) -> None:
        get.side_effect = [
            requests.ConnectionError(),
            make_response(json_data=pikachu_data),
        ]
        with pytest.raises(ApiUnavailableError):
            client.get_pokemon("pikachu")

        assert client.get_pokemon("pikachu").id == 25  # the retry works

    def test_pages_are_cached(
        self, client: PokeApiClient, get: Mock, list_data: dict[str, Any]
    ) -> None:
        get.return_value = make_response(json_data=list_data)

        client.list_pokemon(limit=20, offset=0)
        client.list_pokemon(limit=20, offset=0)

        assert get.call_count == 1


class TestConfiguration:
    def test_sets_a_user_agent(self, session: requests.Session) -> None:
        PokeApiClient(session=session)
        assert str(session.headers["User-Agent"]).startswith("pokedex-cli/")

    def test_ignores_trailing_slash_in_base_url(
        self, session: requests.Session, pikachu_data: dict[str, Any]
    ) -> None:
        client = PokeApiClient(session=session, base_url="http://localhost/api/")
        get: Mock = session.get  # type: ignore[assignment]
        get.return_value = make_response(json_data=pikachu_data)

        client.get_pokemon("pikachu")

        assert get.call_args.args[0] == "http://localhost/api/pokemon/pikachu"

    def test_creates_its_own_session_by_default(self) -> None:
        with PokeApiClient() as client:
            assert isinstance(client._session, requests.Session)

    def test_context_manager_closes_the_session(self) -> None:
        session = Mock(spec=requests.Session)
        session.headers = {}
        with PokeApiClient(session=session):
            session.close.assert_not_called()
        session.close.assert_called_once_with()
