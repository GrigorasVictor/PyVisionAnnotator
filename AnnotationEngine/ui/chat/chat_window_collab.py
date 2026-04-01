"""Collaboration handlers for ChatWindow."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

from PyQt6.QtWidgets import QMessageBox

from core.chat.collab_protocol import COLLAB_HTTP_BASE_DEFAULT, COLLAB_WS_PATH
from core.chat.collab_rest import CollabRestClient
from core.chat.collab_stomp_worker import CollabStompWorker


def start_collab_worker(window) -> None:
    if window._collab_worker and window._collab_worker.isRunning():
        return
    base_url = window.edit_base_url.text().strip() or COLLAB_HTTP_BASE_DEFAULT
    window._collab_ws_url = window._build_ws_url(base_url, COLLAB_WS_PATH)
    window._collab_worker = CollabStompWorker(ws_url=window._collab_ws_url, jwt_token=window._jwt, parent=window)
    window._collab_worker.connected.connect(lambda: window._append_system("Collab websocket connected."))
    window._collab_worker.disconnected.connect(lambda reason: window._append_system(f"Collab: {reason}"))
    window._collab_worker.connection_error.connect(lambda m: window._append_system(f"Collab error: {m}"))
    window._collab_worker.event_received.connect(window._on_collab_event_received)
    window._collab_worker.start()


def collab_client(window) -> CollabRestClient:
    base_url = window.edit_base_url.text().strip() or COLLAB_HTTP_BASE_DEFAULT
    return CollabRestClient(base_url=base_url, jwt_token=window._jwt)


def on_collab_refresh_sessions(window) -> None:
    if not window._jwt:
        QMessageBox.warning(window, "Chat", "Load session and connect first.")
        return
    status, body = window._collab_client().list_sessions()
    window.combo_collab_sessions.clear()
    if status != 200:
        QMessageBox.warning(window, "Chat", f"Cannot load sessions (HTTP {status}).")
        return
    items = body.get("items", []) if isinstance(body, dict) else []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        sid = str(entry.get("sessionId") or "").strip()
        name = str(entry.get("name") or sid)
        if sid:
            window.combo_collab_sessions.addItem(f"{name} [{sid}]", entry)
    window._append_system(f"Loaded {window.combo_collab_sessions.count()} collab sessions.")


def on_collab_join_session(window) -> None:
    data = window.combo_collab_sessions.currentData()
    if not isinstance(data, dict):
        QMessageBox.warning(window, "Chat", "Select a valid session first.")
        return
    window._collab_session = data
    window._collab_version = int(data.get("version") or 0)
    sid = str(data.get("sessionId") or "").strip()
    if not sid:
        QMessageBox.warning(window, "Chat", "Session id missing.")
        return
    if window._collab_worker:
        window._collab_worker.set_active_session(sid)
    status, snap = window._collab_client().get_snapshot(sid)
    if status == 200 and isinstance(snap, dict):
        window.collab_snapshot_received.emit(snap)
        QMessageBox.information(window, "Chat", f"Joined collaboration session: {sid}")
    else:
        QMessageBox.warning(window, "Chat", f"Snapshot failed (HTTP {status}).")


def on_collab_upload_image(window) -> None:
    if not window._collab_session:
        QMessageBox.warning(window, "Chat", "Join a collaboration session first.")
        return
    image_path = ""
    if callable(window._current_image_path_fn):
        image_path = str(window._current_image_path_fn() or "").strip()
    if not image_path:
        QMessageBox.warning(window, "Chat", "No active image in project.")
        return
    status, body = window._collab_client().upload_temp_image(
        session_id=str(window._collab_session.get("sessionId") or ""),
        project_id=str(window._collab_session.get("projectId") or ""),
        image_id=str(window._collab_session.get("imageId") or ""),
        camera_id=str(window._collab_session.get("cameraId") or ""),
        file_path=image_path,
    )
    if status != 200 or not isinstance(body, dict):
        QMessageBox.warning(window, "Chat", f"Upload failed (HTTP {status}).")
        return
    window._append_system(f"Uploaded image for collab: {body.get('fileName')}")
    window.send_collab_event(
        "image.available",
        {
            "fileName": body.get("fileName"),
            "width": body.get("width"),
            "height": body.get("height"),
            "mimeType": body.get("mimeType"),
            "sizeBytes": body.get("sizeBytes"),
            "downloadUrl": body.get("downloadUrl"),
            "expiresAt": body.get("expiresAt"),
        },
    )


def send_collab_event(window, event_type: str, payload: dict[str, Any]) -> bool:
    if not window._collab_worker or not window._collab_session:
        return False
    sid = str(window._collab_session.get("sessionId") or "").strip()
    if not sid:
        return False
    window._collab_version = max(0, int(window._collab_version)) + 1
    envelope = {
        "eventId": str(uuid.uuid4()),
        "type": str(event_type),
        "sessionId": sid,
        "projectId": str(window._collab_session.get("projectId") or ""),
        "imageId": str(window._collab_session.get("imageId") or ""),
        "cameraId": str(window._collab_session.get("cameraId") or ""),
        "actorId": window._user_id,
        "version": window._collab_version,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": payload,
    }
    window._collab_worker.send_event(envelope)
    return True


def on_collab_event_received(window, payload: dict) -> None:
    etype = str(payload.get("type") or "")
    if etype.startswith("annotation."):
        window.collab_event_received.emit(payload)
        return
    if etype == "image.available":
        window._append_system("Collab image.available received.")

