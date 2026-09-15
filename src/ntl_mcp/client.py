"""Minimal Blackboard Learn public REST client for NTULearn."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

import httpx

from ntl_mcp.auth import BASE_URL_DEFAULT


class SessionExpired(Exception):
    """HTTP 401 — BbRouter is no longer accepted."""


class ApiError(Exception):
    def __init__(self, status: int, path: str, body: str) -> None:
        self.status = status
        self.path = path
        self.body = body
        super().__init__(f"Blackboard HTTP {status} at {path}: {body[:240]}")


class BbClient:
    def __init__(self, cookie: str, base_url: str | None = None) -> None:
        self.base_url = (
            base_url
            or os.environ.get("NTULEARN_BASE_URL")
            or BASE_URL_DEFAULT
        ).rstrip("/")
        self._cookie = cookie
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Cookie": f"BbRouter={cookie}",
                "Accept": "application/json",
            },
            timeout=30.0,
            follow_redirects=True,
        )
        self._files = httpx.AsyncClient(
            headers={"Cookie": f"BbRouter={cookie}"},
            timeout=60.0,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._http.aclose()
        await self._files.aclose()

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._http.get(path, params=params)
        if response.status_code == 401:
            raise SessionExpired()
        if not response.is_success:
            raise ApiError(response.status_code, path, response.text)
        if not response.content:
            return {}
        return response.json()

    async def get_paginated(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[Any]:
        query = dict(params or {})
        query.setdefault("limit", 200)
        rows: list[Any] = []
        while True:
            payload = await self.get_json(path, query)
            rows.extend(payload.get("results") or [])
            next_page = (payload.get("paging") or {}).get("nextPage")
            if not next_page:
                break
            if next_page.startswith("http"):
                path = next_page[len(self.base_url) :] or next_page
            else:
                path = next_page
            query = {}
        return rows

    async def download_bytes(self, url: str) -> tuple[bytes, str]:
        if url.startswith("/"):
            url = urljoin(self.base_url + "/", url.lstrip("/"))
        response = await self._files.get(url)
        if response.status_code == 401:
            raise SessionExpired()
        if not response.is_success:
            raise ApiError(response.status_code, url, response.text[:300])
        return response.content, response.headers.get("content-type", "")

    async def me(self) -> dict[str, Any]:
        return await self.get_json("/learn/api/public/v1/users/me")

    async def enrollments(self) -> list[dict[str, Any]]:
        return await self.get_paginated("/learn/api/public/v1/users/me/courses")

    async def course(self, course_id: str) -> dict[str, Any]:
        return await self.get_json(f"/learn/api/public/v1/courses/{course_id}")

    async def contents(self, course_id: str) -> list[dict[str, Any]]:
        return await self.get_paginated(
            f"/learn/api/public/v1/courses/{course_id}/contents"
        )

    async def content_item(self, course_id: str, content_id: str) -> dict[str, Any]:
        return await self.get_json(
            f"/learn/api/public/v1/courses/{course_id}/contents/{content_id}"
        )

    async def content_children(
        self, course_id: str, content_id: str
    ) -> list[dict[str, Any]]:
        return await self.get_paginated(
            f"/learn/api/public/v1/courses/{course_id}/contents/{content_id}/children"
        )

    async def attachments(
        self, course_id: str, content_id: str
    ) -> list[dict[str, Any]]:
        return await self.get_paginated(
            f"/learn/api/public/v1/courses/{course_id}/contents/{content_id}/attachments"
        )

    async def attachment_download_url(
        self, course_id: str, content_id: str, attachment_id: str
    ) -> str:
        path = (
            f"/learn/api/public/v1/courses/{course_id}/contents/"
            f"{content_id}/attachments/{attachment_id}/download"
        )
        return urljoin(self.base_url + "/", path.lstrip("/"))

    async def announcements(self, course_id: str) -> list[dict[str, Any]]:
        return await self.get_paginated(
            f"/learn/api/public/v1/courses/{course_id}/announcements"
        )

    async def calendar_items(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return await self.get_paginated(
            "/learn/api/public/v1/calendars/items", params
        )

    async def gradebook_columns(self, course_id: str) -> list[dict[str, Any]]:
        return await self.get_paginated(
            f"/learn/api/public/v1/courses/{course_id}/gradebook/columns"
        )

    async def gradebook_user(
        self, course_id: str, user_id: str
    ) -> dict[str, Any]:
        return await self.get_json(
            f"/learn/api/public/v1/courses/{course_id}/gradebook/users/{user_id}"
        )
