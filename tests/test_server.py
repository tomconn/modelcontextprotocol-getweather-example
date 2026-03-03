"""Unit tests for server.py."""

import sys
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

import server


# ---------------------------------------------------------------------------
# _assert_local_invocation
# ---------------------------------------------------------------------------

class TestAssertLocalInvocation:
    def test_exits_when_stdin_is_tty(self, monkeypatch):
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        monkeypatch.setattr(sys, "stdin", mock_stdin)
        with pytest.raises(SystemExit):
            server._assert_local_invocation()

    def test_passes_when_stdin_is_pipe(self, monkeypatch):
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        monkeypatch.setattr(sys, "stdin", mock_stdin)
        server._assert_local_invocation()  # must not raise

    def test_passes_when_stdin_has_no_isatty(self, monkeypatch):
        """stdin replaced with a mock lacking isatty() — allow (e.g. test harnesses)."""
        mock_stdin = MagicMock(spec=[])  # no attributes at all
        monkeypatch.setattr(sys, "stdin", mock_stdin)
        server._assert_local_invocation()  # must not raise

    def test_exit_message_mentions_local(self, monkeypatch):
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        monkeypatch.setattr(sys, "stdin", mock_stdin)
        with pytest.raises(SystemExit) as exc_info:
            server._assert_local_invocation()
        assert "local" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# _call_weather_api
# ---------------------------------------------------------------------------

class TestCallWeatherApi:
    async def test_sends_correct_request(self):
        """Verifies URL, headers, and JSON payload."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"response": "Sunny"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            await server._call_weather_api("Sydney")

        mock_client.post.assert_called_once_with(
            server.API_ENDPOINT,
            headers={
                "Authorization": server.API_TOKEN,
                "Content-Type": "application/json",
            },
            json={"query": "What is the weather like in Sydney?"},
        )

    async def test_returns_parsed_json(self):
        payload = {"response": "25°C and sunny"}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = payload

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await server._call_weather_api("Sydney")

        assert result == payload

    async def test_propagates_http_status_error(self):
        mock_request = MagicMock()
        mock_resp = MagicMock(status_code=500, text="Internal Server Error")
        exc = httpx.HTTPStatusError("boom", request=mock_request, response=mock_resp)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = exc

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(httpx.HTTPStatusError):
                await server._call_weather_api("Sydney")

    async def test_uses_env_vars_for_endpoint_and_token(self, monkeypatch):
        monkeypatch.setattr(server, "API_ENDPOINT", "https://example.com/weather")
        monkeypatch.setattr(server, "API_TOKEN", "test-token-xyz")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            await server._call_weather_api("Perth")

        _, kwargs = mock_client.post.call_args
        assert kwargs["headers"]["Authorization"] == "test-token-xyz"
        assert mock_client.post.call_args[0][0] == "https://example.com/weather"

    async def test_query_embeds_city_name(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            await server._call_weather_api("Darwin")

        _, kwargs = mock_client.post.call_args
        assert "Darwin" in kwargs["json"]["query"]


# ---------------------------------------------------------------------------
# get_weather tool
# ---------------------------------------------------------------------------

class TestGetWeather:
    async def test_returns_response_field(self):
        with patch("server._call_weather_api", new=AsyncMock(return_value={"response": "Sunny, 25°C"})):
            result = await server.get_weather("Sydney")
        assert result == "Sunny, 25°C"

    async def test_empty_string_response_is_returned_as_is(self):
        """An empty-string response is valid and must not fall back to str(data)."""
        with patch("server._call_weather_api", new=AsyncMock(return_value={"response": ""})):
            result = await server.get_weather("Sydney")
        assert result == ""

    async def test_missing_response_key_falls_back_to_str(self):
        data = {"weather": "Sunny", "temp": 25}
        with patch("server._call_weather_api", new=AsyncMock(return_value=data)):
            result = await server.get_weather("Sydney")
        assert result == str(data)

    async def test_none_response_value_falls_back_to_str(self):
        data = {"response": None}
        with patch("server._call_weather_api", new=AsyncMock(return_value=data)):
            result = await server.get_weather("Sydney")
        assert result == str(data)

    async def test_http_status_error_returns_formatted_message(self):
        mock_resp = MagicMock(status_code=403, text="Forbidden")
        exc = httpx.HTTPStatusError("forbidden", request=MagicMock(), response=mock_resp)
        with patch("server._call_weather_api", new=AsyncMock(side_effect=exc)):
            result = await server.get_weather("Sydney")
        assert result == "API error 403: Forbidden"

    async def test_generic_exception_returns_formatted_message(self):
        with patch("server._call_weather_api", new=AsyncMock(side_effect=Exception("connection refused"))):
            result = await server.get_weather("Sydney")
        assert result == "Request failed: connection refused"

    async def test_timeout_exception_is_caught(self):
        exc = httpx.TimeoutException("timed out")
        with patch("server._call_weather_api", new=AsyncMock(side_effect=exc)):
            result = await server.get_weather("Brisbane")
        assert "Request failed" in result

    async def test_passes_city_to_api(self):
        mock_api = AsyncMock(return_value={"response": "Hot"})
        with patch("server._call_weather_api", new=mock_api):
            await server.get_weather("Darwin")
        mock_api.assert_called_once_with("Darwin")

    @pytest.mark.parametrize("city", ["Sydney", "Melbourne", "Brisbane", "Perth", "Darwin"])
    async def test_accepts_all_australian_capitals(self, city):
        with patch("server._call_weather_api", new=AsyncMock(return_value={"response": "Fine"})):
            result = await server.get_weather(city)
        assert result == "Fine"
