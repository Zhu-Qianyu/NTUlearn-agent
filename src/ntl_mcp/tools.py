"""MCP tools for NTULearn."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from mcp.server.fastmcp import FastMCP

from ntl_mcp.client import ApiError, BbClient
from ntl_mcp.files import (
    INLINE_LIMIT,
    body_html,
    html_file_links,
    read_small_file,
    unique_path,
)
from ntl_mcp.names import course_code
from ntl_mcp.session import call

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _download_root() -> Path:
    raw = os.environ.get("NTULEARN_DOWNLOAD_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "NTULearn" / "courses"


def _page(rows: list[Any], offset: int, limit: int) -> dict[str, Any]:
    offset = max(0, offset)
    limit = min(_MAX_LIMIT, max(1, limit))
    sliced = rows[offset : offset + limit]
    nxt = offset + limit if offset + limit < len(rows) else None
    return {
        "items": sliced,
        "total": len(rows),
        "count": len(sliced),
        "offset": offset,
        "limit": limit,
        "hasMore": nxt is not None,
        "nextOffset": nxt,
    }


def _strip_content(item: dict[str, Any]) -> dict[str, Any]:
    handler = item.get("contentHandler") or {}
    if not isinstance(handler, dict):
        handler = {}
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "contentHandlerId": handler.get("id"),
        "hasChildren": bool(item.get("hasChildren")),
        "availability": (item.get("availability") or {}).get("available"),
        "modified": item.get("modified"),
    }


async def _enrolled_course_ids(client: BbClient, include_disabled: bool) -> list[str]:
    enrollments = await client.enrollments()
    ids: list[str] = []
    for row in enrollments:
        available = (row.get("availability") or {}).get("available")
        if not include_disabled and available != "Yes":
            continue
        cid = row.get("courseId")
        if cid:
            ids.append(str(cid))
    return ids


async def _course_map(client: BbClient, course_ids: list[str]) -> dict[str, dict[str, Any]]:
    async def one(cid: str) -> tuple[str, dict[str, Any]]:
        try:
            return cid, await client.course(cid)
        except ApiError:
            return cid, {"id": cid, "name": cid}

    pairs = await asyncio.gather(*[one(cid) for cid in course_ids])
    return dict(pairs)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="ntl_list_courses",
        description="List NTULearn courses the current user is enrolled in.",
    )
    async def ntl_list_courses(
        include_disabled: bool = False,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
    ) -> str:
        async def work(client: BbClient) -> str:
            enrollments = await client.enrollments()
            if not include_disabled:
                enrollments = [
                    e
                    for e in enrollments
                    if (e.get("availability") or {}).get("available") == "Yes"
                ]
            ids = [str(e["courseId"]) for e in enrollments if e.get("courseId")]
            details = await _course_map(client, ids)
            accessed = {str(e["courseId"]): e.get("lastAccessed") for e in enrollments}
            rows = []
            for cid in ids:
                course = details.get(cid) or {}
                title = course.get("name") or course.get("displayName") or cid
                rows.append(
                    {
                        "courseId": cid,
                        "code": course_code(str(title), cid),
                        "title": title,
                        "catalogId": course.get("courseId"),
                        "lastAccessed": accessed.get(cid),
                    }
                )
            rows.sort(key=lambda r: r["lastAccessed"] or "", reverse=True)
            return _dumps(_page(rows, offset, limit))

        return await call(work)

    @mcp.tool(
        name="ntl_get_course_contents",
        description="List a course content folder. Omit parent_id for the top level.",
    )
    async def ntl_get_course_contents(
        course_id: str,
        parent_id: str | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
    ) -> str:
        async def work(client: BbClient) -> str:
            if parent_id:
                items = await client.content_children(course_id, parent_id)
            else:
                items = await client.contents(course_id)
            stripped = [_strip_content(i) for i in items]
            return _dumps(_page(stripped, offset, limit))

        return await call(work)

    @mcp.tool(
        name="ntl_search_course_content",
        description="Recursively search one course's content tree by title/description substring.",
    )
    async def ntl_search_course_content(
        course_id: str,
        query: str,
        max_depth: int = 5,
        max_results: int = 50,
    ) -> str:
        needle = query.strip().lower()
        if not needle:
            raise ValueError("query cannot be empty")
        max_depth = min(10, max(1, max_depth))
        max_results = min(_MAX_LIMIT, max(1, max_results))

        async def work(client: BbClient) -> str:
            matches: list[dict[str, Any]] = []
            seen: set[str] = set()
            lock = asyncio.Semaphore(5)

            async def walk(items: list[dict[str, Any]], path: list[str], depth: int) -> None:
                if depth > max_depth or len(matches) >= max_results:
                    return
                child_jobs = []
                for item in items:
                    if len(matches) >= max_results:
                        break
                    item_id = str(item.get("id") or "")
                    if item_id:
                        if item_id in seen:
                            continue
                        seen.add(item_id)
                    title = str(item.get("title") or "")
                    desc = body_html(item)
                    crumb = path + [title]
                    blob = f"{title}\n{desc}".lower()
                    if needle in blob:
                        row = _strip_content(item)
                        row["breadcrumb"] = crumb
                        matches.append(row)
                    if item.get("hasChildren") and item_id and len(matches) < max_results:

                        async def fetch(cid: str = item_id, crumb=crumb) -> None:
                            async with lock:
                                children = await client.content_children(course_id, cid)
                            await walk(children, crumb, depth + 1)

                        child_jobs.append(fetch())
                if child_jobs:
                    await asyncio.gather(*child_jobs)

            top = await client.contents(course_id)
            await walk(top, [], 0)
            return _dumps({"matches": matches, "count": len(matches)})

        return await call(work)

    @mcp.tool(
        name="ntl_get_announcements",
        description="Announcements across enrolled courses, newest first.",
    )
    async def ntl_get_announcements(
        course_ids: list[str] | None = None,
        since: str | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
    ) -> str:
        async def work(client: BbClient) -> str:
            ids = course_ids or await _enrolled_course_ids(client, False)

            async def one(cid: str) -> list[dict[str, Any]]:
                try:
                    rows = await client.announcements(cid)
                except ApiError:
                    return []
                out = []
                for row in rows:
                    item = {
                        "id": row.get("id"),
                        "courseId": cid,
                        "title": row.get("title"),
                        "body": row.get("body"),
                        "created": row.get("created"),
                        "modified": row.get("modified"),
                    }
                    if since and str(item.get("created") or "") < since:
                        continue
                    out.append(item)
                return out

            groups = await asyncio.gather(*[one(cid) for cid in ids])
            flat = [item for group in groups for item in group]
            flat.sort(key=lambda r: r.get("created") or "", reverse=True)
            return _dumps(_page(flat, offset, limit))

        return await call(work)

    @mcp.tool(
        name="ntl_get_upcoming",
        description="Calendar / due dates. type=GradebookColumn for assignments. Defaults to the next 14 days.",
    )
    async def ntl_get_upcoming(
        since: str | None = None,
        until: str | None = None,
        course_ids: list[str] | None = None,
        type: str | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
    ) -> str:
        start = since or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if until:
            end = until
        else:
            end = (datetime.now(timezone.utc) + timedelta(days=14)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        async def work(client: BbClient) -> str:
            ids = course_ids or await _enrolled_course_ids(client, False)

            async def one(cid: str) -> list[dict[str, Any]]:
                params: dict[str, Any] = {
                    "since": start,
                    "until": end,
                    "courseId": cid,
                }
                if type:
                    params["type"] = type
                try:
                    rows = await client.calendar_items(params)
                except ApiError:
                    return []
                cleaned = []
                for row in rows:
                    cleaned.append(
                        {
                            "id": row.get("id"),
                            "type": row.get("type"),
                            "title": row.get("title"),
                            "start": row.get("start"),
                            "end": row.get("end"),
                            "courseId": cid,
                            "calendarName": (row.get("calendarId") or row.get("calendarName")),
                            "eventType": row.get("eventType"),
                        }
                    )
                return cleaned

            groups = await asyncio.gather(*[one(cid) for cid in ids])
            flat = [item for group in groups for item in group]
            flat.sort(key=lambda r: r.get("start") or "")
            return _dumps(_page(flat, offset, limit))

        return await call(work)

    @mcp.tool(
        name="ntl_get_gradebook",
        description="Gradebook columns and scores for enrolled courses.",
    )
    async def ntl_get_gradebook(
        course_ids: list[str] | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
    ) -> str:
        async def work(client: BbClient) -> str:
            me = await client.me()
            user_id = str(me.get("id") or "")
            ids = course_ids or await _enrolled_course_ids(client, False)

            async def one(cid: str) -> dict[str, Any]:
                try:
                    columns = await client.gradebook_columns(cid)
                except ApiError as exc:
                    return {"courseId": cid, "error": str(exc), "columns": []}
                scores: dict[str, Any] = {}
                if user_id:
                    try:
                        gb = await client.gradebook_user(cid, user_id)
                        for col in gb.get("columns") or []:
                            cid_col = str(col.get("id") or col.get("columnId") or "")
                            scores[cid_col] = col
                    except ApiError:
                        pass
                slim = []
                for col in columns:
                    col_id = str(col.get("id") or "")
                    slim.append(
                        {
                            "id": col_id,
                            "name": col.get("name"),
                            "due": (col.get("grading") or {}).get("due"),
                            "score": scores.get(col_id),
                        }
                    )
                return {"courseId": cid, "columns": slim}

            groups = await asyncio.gather(*[one(cid) for cid in ids])
            return _dumps(_page(list(groups), offset, limit))

        return await call(work)

    @mcp.tool(
        name="ntl_download_file",
        description=(
            "Download files attached to a content item. "
            "destination_dir defaults to NTULEARN_DOWNLOAD_DIR or ~/NTULearn/courses."
        ),
    )
    async def ntl_download_file(
        course_id: str,
        content_id: str,
        destination_dir: str | None = None,
    ) -> str:
        async def work(client: BbClient) -> str:
            item = await client.content_item(course_id, content_id)
            title = str(item.get("title") or content_id)
            dest = Path(destination_dir).expanduser() if destination_dir else _download_root()
            dest.mkdir(parents=True, exist_ok=True)
            pairs: list[tuple[str, str]] = []

            try:
                attachments = await client.attachments(course_id, content_id)
            except ApiError:
                attachments = []
            for att in attachments:
                att_id = str(att.get("id") or "")
                if not att_id:
                    continue
                url = await client.attachment_download_url(
                    course_id, content_id, att_id
                )
                filename = str(att.get("fileName") or att.get("name") or f"{att_id}.bin")
                pairs.append((url, filename))

            html = body_html(item)
            pairs.extend(html_file_links(html, client.base_url))

            saved: list[dict[str, Any]] = []
            for url, filename in pairs:
                name = unquote(filename)
                path = unique_path(dest, name)
                data, _mime = await client.download_bytes(url)
                path.write_bytes(data)
                saved.append(
                    {
                        "path": str(path),
                        "bytes": len(data),
                        "filename": path.name,
                        "source": url,
                    }
                )

            return _dumps(
                {
                    "contentId": content_id,
                    "title": title,
                    "destinationDir": str(dest),
                    "files": saved,
                }
            )

        return await call(work)

    @mcp.tool(
        name="ntl_read_file_content",
        description=(
            "Read a small attached file inline (text/PDF/Office). "
            f"Refuses files over {INLINE_LIMIT} bytes — use ntl_download_file instead."
        ),
    )
    async def ntl_read_file_content(
        course_id: str,
        content_id: str,
        max_files: int = 3,
    ) -> str:
        async def work(client: BbClient) -> str:
            item = await client.content_item(course_id, content_id)
            pairs: list[tuple[str, str]] = []
            try:
                attachments = await client.attachments(course_id, content_id)
            except ApiError:
                attachments = []
            for att in attachments:
                att_id = str(att.get("id") or "")
                if not att_id:
                    continue
                url = await client.attachment_download_url(
                    course_id, content_id, att_id
                )
                filename = str(att.get("fileName") or att.get("name") or att_id)
                pairs.append((url, filename))
            pairs.extend(html_file_links(body_html(item), client.base_url))
            if not pairs:
                return _dumps({"error": "No attached files found.", "contentId": content_id})

            texts: list[dict[str, Any]] = []
            skipped: list[str] = []
            for url, filename in pairs[: max(1, max_files)]:
                data, mime = await client.download_bytes(url)
                if len(data) > INLINE_LIMIT:
                    skipped.append(f"{filename} ({len(data)} bytes)")
                    continue
                texts.append(
                    {
                        "filename": filename,
                        "text": read_small_file(data, filename, mime),
                    }
                )
            return _dumps(
                {
                    "contentId": content_id,
                    "title": item.get("title"),
                    "files": texts,
                    "skipped": skipped,
                }
            )

        return await call(work)
