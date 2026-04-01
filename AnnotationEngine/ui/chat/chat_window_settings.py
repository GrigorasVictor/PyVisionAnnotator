"""Session and server settings helpers for ChatWindow."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox

from core.chat.chat_protocol import HTTP_BASE_DEFAULT, WS_URL_DEFAULT
from core.chat.collab_protocol import COLLAB_WS_PATH, COLLAB_WS_URL_DEFAULT
from utils.auth_store import list_saved_sessions, load_auth_payload

_ORG = "PyVisionAnnotator"
_APP = "PyVisionAnnotator"


def load_saved_session(window, show_message: bool, session_name: str | None = None) -> None:
    payload = load_auth_payload(session_name) or {}
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    window._jwt = extract_token(data)
    window._user_id = extract_user_id(data)

    if window._jwt:
        who = window._user_id or "authenticated user"
        window.lbl_session.setText(f"Loaded JWT for {who}")
        if show_message:
            QMessageBox.information(window, "Chat", "Session loaded from saved auth payload.")
    else:
        window.lbl_session.setText("No token found. Use Account login first.")
        if show_message:
            QMessageBox.warning(window, "Chat", "No JWT found in saved session.")


def populate_profiles(window) -> None:
    window.combo_profiles.clear()
    for p in list_saved_sessions():
        try:
            name = p.name
            stem = p.stem
        except Exception:
            continue
        if name == "session.json":
            continue
        window.combo_profiles.addItem(name, stem)


def get_selected_profile(window) -> str | None:
    data = window.combo_profiles.currentData()
    return data if data is not None else None


def extract_token(payload: dict[str, Any]) -> str:
    for key in ("token", "accessToken", "jwt", "access_token"):
        value = payload.get(key)
        if value:
            return str(value)
    nested = payload.get("data")
    if isinstance(nested, dict):
        for key in ("token", "accessToken", "jwt", "access_token"):
            value = nested.get(key)
            if value:
                return str(value)
    return ""


def extract_user_id(payload: dict[str, Any]) -> str:
    for key in ("email", "userId", "username", "sub"):
        value = payload.get(key)
        if value:
            return str(value)
    user = payload.get("user")
    if isinstance(user, dict):
        for key in ("email", "userId", "username"):
            value = user.get(key)
            if value:
                return str(value)
    return ""


def build_ws_url(base_url: str, path: str) -> str:
    parsed = urlparse(str(base_url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return WS_URL_DEFAULT if path == "/ws" else COLLAB_WS_URL_DEFAULT
    scheme = "wss" if parsed.scheme == "https" else "ws"
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{scheme}://{parsed.netloc}{normalized}"


def base_origin(url_value: str) -> str:
    parsed = urlparse(str(url_value or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def load_server_base_default() -> str:
    settings = QSettings(_ORG, _APP)
    saved_base = str(settings.value("server/http_base_url", "") or "").strip()
    if saved_base:
        return saved_base
    auth_login = str(settings.value("auth/login_url", "") or "").strip()
    derived = base_origin(auth_login)
    return derived or HTTP_BASE_DEFAULT


def load_chat_ws_default(base_default: str) -> str:
    settings = QSettings(_ORG, _APP)
    saved = str(settings.value("server/chat_ws_url", "") or "").strip()
    if saved:
        return saved
    return build_ws_url(base_default, "/ws")


def load_collab_ws_default(base_default: str) -> str:
    settings = QSettings(_ORG, _APP)
    saved = str(settings.value("server/collab_ws_url", "") or "").strip()
    if saved:
        if saved.endswith("/annotation/ws"):
            migrated = build_ws_url(base_default, COLLAB_WS_PATH)
            settings.setValue("server/collab_ws_url", migrated)
            return migrated
        return saved
    return build_ws_url(base_default, COLLAB_WS_PATH)


def persist_server_settings(base_url: str, chat_ws: str, collab_ws: str) -> None:
    settings = QSettings(_ORG, _APP)
    settings.setValue("server/http_base_url", base_url)
    settings.setValue("server/chat_ws_url", chat_ws)
    settings.setValue("server/collab_ws_url", collab_ws)

