# runtime-smoke.py
"""Verify the database and combined REST/MCP server without external networking."""

import asyncio
import os
import subprocess
import time
import urllib.error
import urllib.request

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def check_mcp():
    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp", timeout=5, sse_read_timeout=5
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert "search_docs" in {tool.name for tool in tools.tools}
            result = await session.call_tool(
                "search_docs", {"query": "runtime verification"}
            )
            assert not result.isError, result
    print("Streamable HTTP initialization and search_docs passed")


def main():
    os.environ["GNOSIS_MCP_PORT"] = "8000"
    subprocess.run(["gnosis-mcp", "init-db"], check=True, timeout=15)
    subprocess.run(["gnosis-mcp", "check"], check=True, timeout=15)
    server = subprocess.Popen(
        ["gnosis-mcp", "serve", "--transport", "streamable-http", "--rest"]
    )
    try:
        deadline = time.monotonic() + 25
        while True:
            if server.poll() is not None:
                raise RuntimeError(f"Gnosis exited before readiness: {server.returncode}")
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8000/health", timeout=2
                ) as response:
                    assert response.status == 200
                break
            except (urllib.error.URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        asyncio.run(check_mcp())
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == "__main__":
    main()
