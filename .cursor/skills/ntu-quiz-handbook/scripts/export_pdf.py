#!/usr/bin/env python3
"""Export a handbook .docx to PDF. Windows: Word COM. Else: LibreOffice."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def export_word(docx: Path, pdf: Path) -> None:
    import win32com.client  # type: ignore

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(docx), ReadOnly=True)
        try:
            if pdf.exists():
                pdf.unlink()
            # 17 = wdExportFormatPDF
            doc.ExportAsFixedFormat(str(pdf), 17)
        finally:
            doc.Close(False)
    finally:
        word.Quit()


def export_soffice(docx: Path, pdf: Path) -> None:
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if not soffice:
        raise SystemExit("No Microsoft Word and no LibreOffice soffice on PATH")
    outdir = pdf.parent
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)],
        check=True,
    )
    produced = outdir / (docx.stem + ".pdf")
    if produced.resolve() != pdf.resolve():
        if pdf.exists():
            pdf.unlink()
        produced.replace(pdf)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx")
    parser.add_argument("-o", "--pdf", help="Output PDF. Default: same stem next to the docx")
    args = parser.parse_args()

    docx = Path(args.docx).resolve()
    if not docx.is_file():
        raise SystemExit(f"docx not found: {docx}")
    pdf = Path(args.pdf).resolve() if args.pdf else docx.with_suffix(".pdf")
    pdf.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        try:
            export_word(docx, pdf)
            print(str(pdf))
            return
        except Exception as exc:
            print(f"Word COM failed: {exc}", file=sys.stderr)

    export_soffice(docx, pdf)
    print(str(pdf))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
