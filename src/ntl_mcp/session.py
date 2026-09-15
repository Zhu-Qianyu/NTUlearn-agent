"""Process-wide Blackboard client with a single 401 retry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from ntl_mcp.auth import delete_keyring, resolve_cookie
from ntl_mcp.client import BbClient, SessionExpired

T = TypeVar("T")

_client: BbClient | None = None


async def get_client() -> BbClient:
    global _client
    if _client is None:
        _client = BbClient(resolve_cookie())
    return _client


async def drop_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def call(fn: Callable[[BbClient], Awaitable[T]]) -> T:
    client = await get_client()
    try:
        return await fn(client)
    except SessionExpired:
        await drop_client()
        delete_keyring()
        client = await get_client()
        return await fn(client)
