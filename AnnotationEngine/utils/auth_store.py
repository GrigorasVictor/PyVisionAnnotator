"""Persistent storage for authentication payloads."""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QStandardPaths


def _auth_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    root = Path(base) if base else (Path.home() / ".pyvisionannotator")
    return root / "auth"


def get_auth_file_path() -> Path:
    return _auth_dir() / "session.json"


def save_auth_payload(payload: dict) -> Path:
    path = get_auth_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def load_auth_payload() -> dict | None:
    path = get_auth_file_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

