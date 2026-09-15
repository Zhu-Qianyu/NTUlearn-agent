"""stdio MCP entrypoint."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ntl_mcp.tools import register

mcp = FastMCP("ntl-mcp")
register(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
