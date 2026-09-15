"""Course short-name helpers."""

from __future__ import annotations

import re

_CODE = re.compile(r"\b([A-Z]{2,4}\d{4}[A-Z]?)\b")


def course_code(title: str | None, course_id: str) -> str:
    text = (title or "").replace("_", "-").upper()
    match = _CODE.search(text)
    if match:
        return match.group(1)
    cleaned = re.sub(r"[^\w\-]+", "_", course_id).strip("_")
    return cleaned or "unknown"


def safe_folder(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name).strip(" .")
    return cleaned or "untitled"
