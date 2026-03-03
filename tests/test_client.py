"""Unit tests for client.py."""

import sys
import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import client


def _make_text_content(text: str):
    c = MagicMock()
    c.type = "text"
    c.text = text
    return c


def _make_tool(name: str, description: str):
    t = MagicMock()
    t.name = name
    t.description = description
    return t


def _build_session_mock(tools=None, call_result_texts=None):
    """Return (session_mock, session_ctx_mock)."""
    tools = tools or [_make_tool("get_weather", "Get weather for a city.")]
    call_result_texts = call_result_texts or ["Sunny, 25°C"]

    mock_result = MagicMock()
    mock_result.content = [_make_text_content(t) for t in call_result_texts]

    mock_tools_resp = MagicMock()
    mock_tools_resp.tools = tools

    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value=mock_tools_resp)
    session.call_tool = AsyncMock(return_value=mock_result)

    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=session)
    session_ctx.__aexit__ = AsyncMock(return_value=False)

    return session, session_ctx


def _build_stdio_mock():
    """Return (read, write, stdio_ctx_mock)."""
    read = AsyncMock()
    write = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=(read, write))
    ctx.__aexit__ = AsyncMock(return_value=False)
    return read, write, ctx


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

class TestRun:
    async def test_calls_initialize(self):
        session, session_ctx = _build_session_mock()
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx), \
             patch("client.ClientSession", return_value=session_ctx):
            await client.run("Sydney")

        session.initialize.assert_called_once()

    async def test_calls_list_tools(self):
        session, session_ctx = _build_session_mock()
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx), \
             patch("client.ClientSession", return_value=session_ctx):
            await client.run("Sydney")

        session.list_tools.assert_called_once()

    async def test_calls_get_weather_with_city(self):
        session, session_ctx = _build_session_mock()
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx), \
             patch("client.ClientSession", return_value=session_ctx):
            await client.run("Brisbane")

        session.call_tool.assert_called_once_with("get_weather", {"city": "Brisbane"})

    async def test_prints_tool_result(self, capsys):
        session, session_ctx = _build_session_mock(call_result_texts=["Hot and humid, 32°C"])
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx), \
             patch("client.ClientSession", return_value=session_ctx):
            await client.run("Darwin")

        captured = capsys.readouterr()
        assert "Hot and humid, 32°C" in captured.out

    async def test_prints_available_tools(self, capsys):
        tools = [_make_tool("get_weather", "Returns weather info.")]
        session, session_ctx = _build_session_mock(tools=tools)
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx), \
             patch("client.ClientSession", return_value=session_ctx):
            await client.run("Perth")

        captured = capsys.readouterr()
        assert "get_weather" in captured.out
        assert "Returns weather info." in captured.out

    async def test_passes_server_script_path_to_stdio_client(self):
        session, session_ctx = _build_session_mock()
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx) as mock_stdio, \
             patch("client.ClientSession", return_value=session_ctx):
            await client.run("Sydney")

        args, _ = mock_stdio.call_args
        server_params = args[0]
        assert server_params.command == sys.executable
        assert str(client.SERVER_SCRIPT) in server_params.args

    async def test_skips_non_text_content(self, capsys):
        """Content items whose type != 'text' must be silently skipped."""
        image_content = MagicMock()
        image_content.type = "image"
        # no .text attribute to ensure AttributeError would occur if accessed
        del image_content.text

        mock_result = MagicMock()
        mock_result.content = [image_content]

        session, session_ctx = _build_session_mock()
        session.call_tool = AsyncMock(return_value=mock_result)
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx), \
             patch("client.ClientSession", return_value=session_ctx):
            # Must not raise AttributeError
            await client.run("Melbourne")

    async def test_multiple_text_content_blocks_all_printed(self, capsys):
        mock_result = MagicMock()
        mock_result.content = [
            _make_text_content("Morning: 18°C"),
            _make_text_content("Afternoon: 26°C"),
        ]

        session, session_ctx = _build_session_mock()
        session.call_tool = AsyncMock(return_value=mock_result)
        _, _, stdio_ctx = _build_stdio_mock()

        with patch("client.stdio_client", return_value=stdio_ctx), \
             patch("client.ClientSession", return_value=session_ctx):
            await client.run("Sydney")

        captured = capsys.readouterr()
        assert "Morning: 18°C" in captured.out
        assert "Afternoon: 26°C" in captured.out


# ---------------------------------------------------------------------------
# SERVER_SCRIPT constant
# ---------------------------------------------------------------------------

class TestServerScriptPath:
    def test_server_script_is_absolute(self):
        assert client.SERVER_SCRIPT.is_absolute()

    def test_server_script_points_to_server_py(self):
        assert client.SERVER_SCRIPT.name == "server.py"

    def test_server_script_exists(self):
        assert client.SERVER_SCRIPT.exists()
