"""Build a source zip for manual GitHub upload. No venv, cookies, or course files."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ntl-mcp-0.1.0.zip"

SKIP_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    "courses",
    ".python-version",
    "dist",
    "build",
}
SKIP_SUFFIXES = {".zip", ".pyc", ".pyo"}
SKIP_NAMES = {".ntl-cookie", ".env"}


def keep(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = set(rel.parts)
    if parts & SKIP_DIRS:
        return False
    if path.suffix in SKIP_SUFFIXES:
        return False
    if path.name in SKIP_NAMES or path.name.endswith(".egg-info"):
        return False
    return True


def main() -> None:
    files = [p for p in ROOT.rglob("*") if p.is_file() and keep(p)]
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())
    print(f"Wrote {OUT} ({len(files)} files)")


if __name__ == "__main__":
    main()
