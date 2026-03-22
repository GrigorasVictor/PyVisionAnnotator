"""Persistent storage for authentication payloads.

Enhancements:
- Support multiple saved sessions (one file per profile).
- If an email can be extracted from the payload it will be used as filename
  (sanitized). Otherwise a timestamp-based filename is used.
- The default file `session.json` is still maintained and updated to contain
  the last-saved session for backward compatibility.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import QStandardPaths


def _auth_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    root = Path(base) if base else (Path.home() / ".pyvisionannotator")
    return root / "auth"


def _sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe as a filename on Windows/Unix.

    We avoid characters forbidden on Windows: <>:"/\\|?* and also strip
    control characters. Keep '@' and '.' so email-like names remain readable.
    """
    forbidden = '<>:"/\\|?*'
    out = ''.join('_' if c in forbidden or ord(c) < 32 else c for c in name)
    return out.strip() or "session"


def _extract_email(payload: dict) -> str | None:
    """Search payload (recursively) for an email-like string and return it.

    This is more robust than checking a few fixed keys because different
    backends may nest the email in different shapes. We perform a depth-first
    search through dicts and lists and return the first string containing '@'.
    """
    if not isinstance(payload, dict):
        return None

    def _find(obj):
        if isinstance(obj, str):
            if "@" in obj:
                return obj
            return None
        if isinstance(obj, dict):
            # Check common keys first for a sensible match
            for key in ("email", "userId", "username", "sub"):
                v = obj.get(key)
                if isinstance(v, str) and "@" in v:
                    return v
            # Otherwise depth-search
            for v in obj.values():
                res = _find(v)
                if res:
                    return res
            return None
        if isinstance(obj, list):
            for item in obj:
                res = _find(item)
                if res:
                    return res
            return None
        return None

    # If wrapper contains 'data', start there; else search whole payload
    start = payload.get("data") if payload.get("data") is not None else payload
    return _find(start)  # may return None


def get_auth_file_path(session_name: str | None = None) -> Path:
    """Return the Path of the session file to use.

    If the environment variable PYVIZ_AUTH_PATH is set it is taken as an
    absolute path to the file. If session_name is provided, the file used is
    '<auth_dir>/<session_name>.json'. Otherwise default to 'session.json'.
    """
    env_path = os.getenv("PYVIZ_AUTH_PATH")
    if env_path:
        return Path(env_path)
    if session_name:
        return _auth_dir() / f"{_sanitize_filename(session_name)}.json"
    return _auth_dir() / "session.json"


def list_saved_sessions() -> Iterable[Path]:
    """List all saved session files in the auth dir (excluding missing dir).

    Returns full Paths. This can be used by a UI to present profiles.
    """
    d = _auth_dir()
    if not d.exists():
        return []
    return sorted(p for p in d.iterdir() if p.is_file() and p.suffix == ".json")


def save_auth_payload(payload: dict, session_name: str | None = None) -> Path:
    """Save the payload to disk.

    Behavior:
    - If session_name provided, use it.
    - Else attempt to extract an email from payload and use that as session name.
    - Else fall back to a timestamp-based filename.
    - Always update the default 'session.json' to contain the last-saved payload
      for backward compatibility with callers that rely on the default path.
    Returns the Path where the payload was written (the profile file).
    """
    # Determine session filename
    name = session_name
    if not name:
        email = _extract_email(payload)
        if email:
            name = email
        else:
            # Use timezone-aware UTC now for filename
            name = datetime.now(timezone.utc).strftime("session_%Y%m%d_%H%M%S")

    path = get_auth_file_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    # Also update default session.json for backward compatibility
    default_path = _auth_dir() / "session.json"
    try:
        default_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    except Exception:
        # If for some reason we cannot write the default, ignore (caller can still
        # access the profile file returned above).
        pass

    return path


def load_auth_payload(session_name: str | None = None) -> dict | None:
    """Load a session payload from disk.

    If session_name is None, the default 'session.json' (or env override)
    is loaded. If a session_name is provided it will load the corresponding
    profile file '<session_name>.json'.
    """
    path = get_auth_file_path(session_name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None




