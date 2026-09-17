#!/usr/bin/env python3
"""Dump 1-based page text from a lecture PDF so the agent can pick screenshot pages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("-o", "--out", help="UTF-8 text dump. Default: stdout")
    parser.add_argument("--max-chars", type=int, default=4000, help="Cap per page")
    args = parser.parse_args()

    pdf = Path(args.pdf)
    if not pdf.is_file():
        raise SystemExit(f"PDF not found: {pdf}")

    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            import fitz
        except ImportError:
            raise SystemExit("Need pypdf or pymupdf")
        doc = fitz.open(pdf)
        chunks = []
        for i, page in enumerate(doc, start=1):
            text = (page.get_text() or "").strip()
            if args.max_chars:
                text = text[: args.max_chars]
            chunks.append(f"\n===== {pdf.name} PAGE {i} =====\n{text}\n")
        body = "".join(chunks)
        if args.out:
            Path(args.out).write_text(body, encoding="utf-8", errors="replace")
            print(f"wrote {args.out} pages={doc.page_count} chars={len(body)}")
        else:
            sys.stdout.write(body)
        return

    reader = PdfReader(str(pdf))
    chunks = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if args.max_chars:
            text = text[: args.max_chars]
        chunks.append(f"\n===== {pdf.name} PAGE {i} =====\n{text}\n")
    body = "".join(chunks)
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8", errors="replace")
        print(f"wrote {args.out} pages={len(reader.pages)} chars={len(body)}")
    else:
        sys.stdout.write(body)


if __name__ == "__main__":
    main()
