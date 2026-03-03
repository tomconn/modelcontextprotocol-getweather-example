# getWeatherMCP

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) demo that exposes an Australian weather tool backed by an AWS Bedrock Agent.

```
MCP Client (client.py)
      │  stdio
      ▼
MCP Server (server.py)
      │  HTTPS POST
      ▼
API Gateway → Lambda Proxy → Bedrock Agent (GetWeather) → Knowledge Base
```

## Files

| File | Purpose |
|---|---|
| `server.py` | MCP server — exposes the `get_weather` tool |
| `client.py` | MCP client — launches the server and calls the tool |
| `tests/test_server.py` | Unit tests for the server |
| `tests/test_client.py` | Unit tests for the client |
| `pyproject.toml` | Project metadata and dependencies |
| `uv.lock` | Locked dependency versions (committed, do not edit manually) |

## Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

Install dependencies and create the virtual environment:

```bash
uv sync
```

## Running the client

The client starts the server automatically as a subprocess over stdio, then calls `get_weather`.

```bash
# Default city: Sydney
uv run python client.py

# Specify a city
uv run python client.py Brisbane
uv run python client.py Perth
uv run python client.py Darwin
```

Example output:

```
Available tools:
  - get_weather: Get the current weather for an Australian city.

Calling get_weather(city='Sydney') ...

The current weather in Sydney is 25°C with sunny and clear skies.
```

## Running the server standalone

The server speaks the MCP stdio protocol and is not intended to be run directly, but you can confirm it starts cleanly:

```bash
uv run python server.py
# Waits for JSON-RPC input on stdin — Ctrl-C to exit
```

## Configuration

The server reads two environment variables. Both have working defaults pointing at the deployed PoC endpoint.

| Variable | Default | Description |
|---|---|---|
| `WEATHER_API_ENDPOINT` | `https://nhy6ulzhfj.execute-api.ap-southeast-2.amazonaws.com/prod/weather` | API Gateway URL |
| `WEATHER_API_TOKEN` | `weather-poc-token-2026` | Bearer token sent in the `Authorization` header |

Override them to point at a different environment:

```bash
export WEATHER_API_ENDPOINT=https://your-endpoint/prod/weather
export WEATHER_API_TOKEN=your-token
uv run python client.py Sydney
```

## MCP tool reference

### `get_weather`

Get the current weather for an Australian city.

**Input**

| Parameter | Type | Description |
|---|---|---|
| `city` | `string` | City name, e.g. `Sydney`, `Melbourne`, `Brisbane`, `Perth`, `Darwin` |

**Output**

A plain-text string with the weather description returned by the Bedrock Agent.

**Error responses**

| Condition | Returned string |
|---|---|
| HTTP error from API Gateway | `API error <status>: <body>` |
| Network / timeout failure | `Request failed: <message>` |

## Running the tests

```bash
uv run --dev pytest
```

All 29 tests run offline using mocks — no AWS credentials or network access required.

```
============================= test session starts ==============================
collected 29 items

tests/test_client.py::TestRun::test_calls_initialize PASSED
tests/test_client.py::TestRun::test_calls_list_tools PASSED
...
tests/test_server.py::TestGetWeather::test_accepts_all_australian_capitals[Darwin] PASSED

============================== 29 passed in 0.62s ==============================
```
