"""MCP server that exposes a get_weather tool backed by a remote weather API."""

import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("get-weather")

API_ENDPOINT = os.getenv(
    "WEATHER_API_ENDPOINT",
    "https://nhy6ulzhfj.execute-api.ap-southeast-2.amazonaws.com/prod/weather",
)
API_TOKEN = os.getenv("WEATHER_API_TOKEN", "weather-poc-token-2026")


async def _call_weather_api(city: str) -> dict[str, Any]:
    headers = {"Authorization": API_TOKEN, "Content-Type": "application/json"}
    payload = {"query": f"What is the weather like in {city}?"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(API_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_weather(city: str) -> str:
    """Get the current weather for an Australian city.

    Args:
        city: Name of the Australian city (e.g. Sydney, Melbourne, Brisbane, Perth, Darwin)
    """
    try:
        data = await _call_weather_api(city)
    except httpx.HTTPStatusError as exc:
        return f"API error {exc.response.status_code}: {exc.response.text}"
    except Exception as exc:
        return f"Request failed: {exc}"

    # The API Gateway / Lambda proxy returns {"response": "<text>"}
    response = data.get("response")
    return response if response is not None else str(data)


def _assert_local_invocation() -> None:
    """Exit if stdin is a TTY, which indicates an interactive or remote session.

    This server communicates over stdio and must be launched as a subprocess
    by a local MCP host.  A TTY on stdin means it is being run interactively
    (e.g. directly in a shell or over SSH), which is not a supported use-case.
    """
    try:
        if sys.stdin.isatty():
            sys.exit(
                "ERROR: This MCP server must be launched by a local MCP host "
                "via stdio, not run interactively."
            )
    except AttributeError:
        pass  # stdin replaced (e.g. during tests) — allow


if __name__ == "__main__":
    _assert_local_invocation()
    mcp.run(transport="stdio")
