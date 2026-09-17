#!/usr/bin/env python3
"""Render selected PDF pages to JPEG snapshots + meta.json for the handbook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_pages(spec: str, n_pages: int) -> list[int]:
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            lo, hi = int(a), int(b)
            pages.extend(range(lo, hi + 1))
        else:
            pages.append(int(part))
    out: list[int] = []
    seen: set[int] = set()
    for p in pages:
        if p < 1 or p > n_pages:
            raise SystemExit(f"Page {p} out of range 1..{n_pages}")
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Lecture PDF")
    parser.add_argument("--code", required=True, help="Short source code, e.g. W1 or IMO")
    parser.add_argument("--pages", required=True, help="1-based pages, e.g. 3,6,10-12")
    parser.add_argument("--out", required=True, help="slide_snaps directory")
    parser.add_argument("--dpi", type=int, default=140)
    parser.add_argument("--quality", type=int, default=70)
    args = parser.parse_args()

    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise SystemExit("Need PyMuPDF: pip install pymupdf")

    pdf = Path(args.pdf)
    if not pdf.is_file():
        raise SystemExit(f"PDF not found: {pdf}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "meta.json"
    meta: dict = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    doc = fitz.open(pdf)
    pages = parse_pages(args.pages, doc.page_count)
    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    written = []
    for page_no in pages:
        page = doc[page_no - 1]
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        name = f"{args.code}_p{page_no:02d}.jpg"
        dest = out / name
        pix.save(str(dest), jpg_quality=args.quality)
        key = f"{args.code}_{page_no}"
        meta[key] = {"file": name, "w": pix.width, "h": pix.height, "pdf": str(pdf), "page": page_no}
        written.append(name)

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "pages": pages, "files": written, "meta": str(meta_path)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
