"""Session cookie resolution for NTULearn.

Windows never reads Chrome or Edge (App-Bound Encryption hangs MCP hosts).
Order: Windows Credential Manager, optional Firefox, then NTULEARN_COOKIE.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)

BASE_URL_DEFAULT = "https://ntulearn.ntu.edu.sg"
COOKIE_NAME = "BbRouter"
DOMAIN = "ntulearn.ntu.edu.sg"
KEYRING_SERVICE = "ntl-mcp"
KEYRING_USER = "BbRouter"


class CookieError(RuntimeError):
    """No usable BbRouter cookie could be resolved."""


def normalize_cookie(raw: str) -> str:
    value = raw.strip().strip('"').strip("'")
    if value.lower().startswith("bbrouter="):
        value = value.split("=", 1)[1].strip()
    if value and not value.startswith("expires:") and value[:1].isdigit():
        value = f"expires:{value}"
    return value


def is_valid_cookie(value: str | None) -> bool:
    if not value:
        return False
    if "\r" in value or "\n" in value or "\x00" in value:
        return False
    return value.startswith("expires:") and "id:" in value


def _keyring_mod():
    try:
        import keyring
    except ImportError:
        return None
    return keyring


def read_keyring() -> str | None:
    keyring = _keyring_mod()
    if keyring is None:
        return None
    try:
        value = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    except Exception as exc:
        logger.debug("keyring read failed: %s", exc)
        return None
    value = normalize_cookie(value) if value else None
    return value if is_valid_cookie(value) else None


def write_keyring(value: str) -> bool:
    value = normalize_cookie(value)
    if not is_valid_cookie(value):
        return False
    keyring = _keyring_mod()
    if keyring is None:
        return False
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, value)
    except Exception as exc:
        logger.debug("keyring write failed: %s", exc)
        return False
    return True


def delete_keyring() -> None:
    keyring = _keyring_mod()
    if keyring is None:
        return
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except Exception as exc:
        logger.debug("keyring delete failed: %s", exc)


def read_firefox() -> str | None:
    """Read BbRouter from Firefox only. Never call Chrome/Edge getters."""
    try:
        import browser_cookie3
    except ImportError:
        return None
    try:
        jar = browser_cookie3.firefox(domain_name=DOMAIN)
    except Exception as exc:
        logger.debug("Firefox cookie read skipped: %s", exc)
        return None
    for cookie in jar:
        if cookie.name == COOKIE_NAME:
            value = normalize_cookie(cookie.value or "")
            if is_valid_cookie(value):
                return value
    return None


def read_env() -> str | None:
    raw = os.environ.get("NTULEARN_COOKIE", "").strip()
    if not raw:
        return None
    value = normalize_cookie(raw)
    return value if is_valid_cookie(value) else None


def resolve_cookie(*, persist: bool = True) -> str:
    firefox = read_firefox()
    if firefox:
        if persist:
            write_keyring(firefox)
        return firefox

    stored = read_keyring()
    if stored:
        return stored

    env = read_env()
    if env:
        if persist:
            write_keyring(env)
        return env

    raise CookieError(
        "No NTULearn cookie found. On Windows, Chrome/Edge cookies cannot be "
        "read. Either log into https://ntulearn.ntu.edu.sg in Firefox, or copy "
        "the BbRouter cookie and run: ntl-save-cookie"
    )


def save_cookie_main() -> None:
    parser = argparse.ArgumentParser(
        description="Save a BbRouter cookie into the OS credential store."
    )
    parser.add_argument(
        "cookie",
        nargs="?",
        help="BbRouter value (starts with expires:). If omitted, read stdin.",
    )
    args = parser.parse_args()
    raw = args.cookie if args.cookie else sys.stdin.read()
    value = normalize_cookie(raw)
    if not is_valid_cookie(value):
        print(
            "Invalid cookie. Paste the BbRouter value from DevTools "
            "(Application → Cookies → ntulearn.ntu.edu.sg → BbRouter).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not write_keyring(value):
        print("Could not write to the OS credential store.", file=sys.stderr)
        raise SystemExit(1)
    print("Saved BbRouter to the OS credential store (ntl-mcp).")
