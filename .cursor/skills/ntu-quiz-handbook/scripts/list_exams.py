#!/usr/bin/env python3
"""List upcoming NTULearn quizzes / tests / CA items for handbook selection.

Does not print cookies. Requires a saved BbRouter (ntl-save-cookie or Firefox).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOTS = [
    Path(__file__).resolve().parents[4] / "src",
    Path(r"F:/ntulearn/src"),
]
for root in ROOTS:
    if (root / "ntl_mcp").is_dir():
        sys.path.insert(0, str(root))
        break

from ntl_mcp.auth import CookieError, resolve_cookie  # noqa: E402
from ntl_mcp.client import BbClient  # noqa: E402
from ntl_mcp.names import course_code  # noqa: E402

QUIZ_RE = re.compile(
    r"quiz|test|mid[- ]?term|ca\s*\d|continual assessment|测验|考试",
    re.I,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _match(title: str) -> bool:
    return bool(QUIZ_RE.search(title or ""))


async def collect(until_days: int) -> dict:
    cookie = resolve_cookie(persist=False)
    client = BbClient(cookie)
    try:
        enrollments = await client.enrollments()
        enrollments = [
            e
            for e in enrollments
            if (e.get("availability") or {}).get("available") == "Yes" and e.get("courseId")
        ]
        ids = [str(e["courseId"]) for e in enrollments]
        courses = {}
        for cid in ids:
            try:
                courses[cid] = await client.course(cid)
            except Exception:
                courses[cid] = {"id": cid, "name": cid}

        def code_of(cid: str) -> str:
            course = courses.get(cid) or {}
            return course_code(course.get("name") or course.get("displayName"), cid)

        since = _now() - timedelta(days=1)
        until = _now() + timedelta(days=until_days)
        calendar_rows = []
        announcements = []
        gradebook = []
        for cid in ids:
            code = code_of(cid)
            name = (courses.get(cid) or {}).get("name") or code
            try:
                items = await client.calendar_items(
                    {
                        "since": _iso(since),
                        "until": _iso(until),
                        "courseId": cid,
                    }
                )
            except Exception:
                items = []
            for row in items:
                title = str(row.get("title") or "")
                calendar_rows.append(
                    {
                        "courseId": cid,
                        "courseCode": code,
                        "courseName": name,
                        "source": "calendar",
                        "title": title,
                        "start": row.get("start"),
                        "end": row.get("end"),
                        "quizLike": _match(title),
                    }
                )
            try:
                anns = await client.announcements(cid)
            except Exception:
                anns = []
            for row in anns:
                title = str(row.get("title") or "")
                body = str(row.get("body") or "")
                blob = title + " " + body
                if _match(blob):
                    announcements.append(
                        {
                            "courseId": cid,
                            "courseCode": code,
                            "courseName": name,
                            "source": "announcement",
                            "title": title,
                            "created": row.get("created"),
                            "quizLike": True,
                        }
                    )
            try:
                columns = await client.gradebook_columns(cid)
            except Exception:
                columns = []
            for col in columns:
                title = str(col.get("name") or "")
                due = (col.get("grading") or {}).get("due")
                if _match(title):
                    gradebook.append(
                        {
                            "courseId": cid,
                            "courseCode": code,
                            "courseName": name,
                            "source": "gradebook",
                            "title": title,
                            "start": due,
                            "quizLike": True,
                        }
                    )

        exams = [r for r in calendar_rows if r["quizLike"]]
        exams.extend(announcements)
        exams.extend(gradebook)
        exams.sort(key=lambda r: r.get("start") or r.get("created") or "")
        numbered = []
        for i, row in enumerate(exams, start=1):
            numbered.append({"n": i, **row})
        return {
            "generatedAt": _iso(_now()),
            "courses": [
                {
                    "courseId": cid,
                    "courseCode": code_of(cid),
                    "name": (courses[cid] or {}).get("name"),
                }
                for cid in ids
            ],
            "exams": numbered,
            "otherCalendar": [r for r in calendar_rows if not r["quizLike"]],
        }
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--until-days", type=int, default=120)
    parser.add_argument("-o", "--out", help="Write JSON here")
    args = parser.parse_args()
    try:
        payload = asyncio.run(collect(args.until_days))
    except CookieError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
