"""Simple MCP client that calls the get_weather tool on the local MCP server."""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_SCRIPT = Path(__file__).parent / "server.py"


async def run(city: str) -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Show available tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()

            # Call get_weather
            print(f"Calling get_weather(city={city!r}) ...\n")
            result = await session.call_tool("get_weather", {"city": city})

            for content in result.content:
                if content.type == "text":
                    print(content.text)


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Sydney"
    asyncio.run(run(city))
