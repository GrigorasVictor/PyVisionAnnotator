"""Collaboration handlers for ChatWindow."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import mimetypes
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from PyQt6.QtWidgets import QMessageBox

from core.chat.collab_protocol import COLLAB_HTTP_BASE_DEFAULT, COLLAB_WS_PATH
from core.chat.collab_rest import CollabRestClient
from core.chat.collab_stomp_worker import CollabStompWorker


_CHUNK_TRIGGER_BYTES = 24 * 1024
# Keep chunk data conservative; WS envelope/headers add overhead on top of the chunk payload.
_CHUNK_SIZE_CHARS = 8 * 1024
_CHUNK_MAX_RETRIES = 2


def _ensure_sync_state(window) -> None:
    if not hasattr(window, "_collab_processed_event_ids"):
        window._collab_processed_event_ids = set()
    if not hasattr(window, "_collab_last_version_by_session"):
        window._collab_last_version_by_session = {}
    if not hasattr(window, "_collab_synced_sessions"):
        window._collab_synced_sessions = set()
    if not hasattr(window, "_collab_chunk_transfers"):
        window._collab_chunk_transfers = {}
    if not hasattr(window, "_collab_chunk_by_original_event"):
        window._collab_chunk_by_original_event = {}


def _build_event_envelope(window, event_type: str, payload: dict[str, Any], sid: str) -> dict[str, Any]:
    return {
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


def _chunkify_text(text: str, chunk_size: int) -> list[str]:
    size = max(1024, int(chunk_size))
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def _send_chunked_event(window, original_envelope: dict[str, Any], retry_count: int = 0) -> bool:
    etype = str(original_envelope.get("type") or "")
    if etype == "annotation.chunk":
        window._append_system("Cannot sync annotation right now.")
        return False

    sid = str(original_envelope.get("sessionId") or "").strip()
    if not sid:
        window._append_system("Cannot sync annotation: missing session.")
        return False

    try:
        original_json = json.dumps(original_envelope, ensure_ascii=True, separators=(",", ":"))
    except Exception:
        window._append_system("Cannot sync annotation right now.")
        return False

    b64 = base64.b64encode(original_json.encode("utf-8")).decode("ascii")
    chunks = _chunkify_text(b64, _CHUNK_SIZE_CHARS)
    total = len(chunks)
    if total <= 0:
        window._append_system("Cannot sync annotation right now.")
        return False

    chunk_id = str(uuid.uuid4())
    original_event_id = str(original_envelope.get("eventId") or "")
    if original_event_id:
        window._collab_worker._seen_event_ids.add(original_event_id)

    window._collab_chunk_transfers[chunk_id] = {
        "original": original_envelope,
        "retry": int(retry_count),
        "total": total,
    }
    if original_event_id:
        window._collab_chunk_by_original_event[original_event_id] = chunk_id

    for index, segment in enumerate(chunks):
        chunk_payload = {
            "chunkId": chunk_id,
            "sessionId": sid,
            "originalType": etype,
            "index": index,
            "total": total,
            "encoding": "base64",
            "data": segment,
        }
        # Keep same version for all chunks belonging to the same logical event.
        chunk_envelope = dict(original_envelope)
        chunk_envelope["eventId"] = str(uuid.uuid4())
        chunk_envelope["type"] = "annotation.chunk"
        chunk_envelope["payload"] = chunk_payload
        window._collab_worker._seen_event_ids.add(chunk_envelope["eventId"])
        window._collab_worker.send_event(chunk_envelope)

    return True


def _maybe_send_chunked(window, envelope: dict[str, Any]) -> bool:
    etype = str(envelope.get("type") or "")
    if etype not in ("annotation.create", "annotation.update", "annotation.delete"):
        return False

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return False

    # Always chunk mask create/update events to avoid large inline WS payloads.
    payload_type = str(payload.get("type") or "").strip().lower()
    if etype in ("annotation.create", "annotation.update") and payload_type == "mask":
        return _send_chunked_event(window, envelope, retry_count=0)

    # Chunk only large annotation events; small events stay regular WS sends.
    try:
        payload_size = len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))
    except Exception:
        return False
    if payload_size < _CHUNK_TRIGGER_BYTES:
        return False

    return _send_chunked_event(window, envelope, retry_count=0)


def _handle_chunk_error(window, envelope: dict[str, Any]) -> None:
    data = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    chunk_id = str(data.get("chunkId") or "").strip()
    if not chunk_id:
        return

    transfer = window._collab_chunk_transfers.get(chunk_id)
    if not isinstance(transfer, dict):
        return

    retry_count = int(transfer.get("retry") or 0)
    original = transfer.get("original") if isinstance(transfer.get("original"), dict) else None
    window._collab_chunk_transfers.pop(chunk_id, None)

    if not isinstance(original, dict):
        return
    if retry_count >= _CHUNK_MAX_RETRIES:
        window._append_system("Sync failed. Please try again.")
        return

    next_try = retry_count + 1
    window._append_system("Retrying sync...")
    _send_chunked_event(window, original, retry_count=next_try)


def _handle_chunk_ack(window, envelope: dict[str, Any]) -> None:
    data = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    chunk_id = str(data.get("chunkId") or "").strip()
    if not chunk_id:
        return
    transfer = window._collab_chunk_transfers.pop(chunk_id, None)
    if not isinstance(transfer, dict):
        return
    original = transfer.get("original") if isinstance(transfer.get("original"), dict) else {}
    original_event_id = str(original.get("eventId") or "").strip()
    if original_event_id:
        window._collab_chunk_by_original_event.pop(original_event_id, None)


def _session_id_from_event(envelope: dict[str, Any]) -> str:
    return str(envelope.get("sessionId") or "").strip()


def _event_version(envelope: dict[str, Any]) -> int:
    try:
        return int(envelope.get("version") or 0)
    except Exception:
        return 0


def _upsert_session_in_combo(window, entry: dict[str, Any]) -> None:
    sid = str(entry.get("sessionId") or "").strip()
    if not sid:
        return
    name = str(entry.get("name") or sid)
    selected_sid = ""
    cur_data = window.combo_collab_sessions.currentData()
    if isinstance(cur_data, dict):
        selected_sid = str(cur_data.get("sessionId") or "").strip()

    idx = -1
    for i in range(window.combo_collab_sessions.count()):
        data = window.combo_collab_sessions.itemData(i)
        if isinstance(data, dict) and str(data.get("sessionId") or "").strip() == sid:
            idx = i
            break
    if idx >= 0:
        window.combo_collab_sessions.setItemText(idx, f"{name} [{sid}]")
        window.combo_collab_sessions.setItemData(idx, entry)
    else:
        window.combo_collab_sessions.addItem(f"{name} [{sid}]", entry)

    if selected_sid and sid == selected_sid:
        new_idx = window.combo_collab_sessions.findText(f"{name} [{sid}]")
        if new_idx >= 0:
            window.combo_collab_sessions.setCurrentIndex(new_idx)


def start_collab_worker(window) -> None:
    if window._collab_worker and window._collab_worker.isRunning():
        return
    base_url = window.edit_base_url.text().strip() or COLLAB_HTTP_BASE_DEFAULT
    window._collab_ws_url = window._build_ws_url(base_url, COLLAB_WS_PATH)
    window._collab_worker = CollabStompWorker(ws_url=window._collab_ws_url, jwt_token=window._jwt, parent=window)

    def _on_connected() -> None:
        window._append_system("Collab websocket connected.")
        # Auto-load rooms on connect so Join works immediately without pressing Load Sessions.
        on_collab_refresh_sessions(window, silent=True)
        sid = str(window._collab_session.get("sessionId") or "").strip() if isinstance(window._collab_session, dict) else ""
        if sid and window._collab_worker:
            window._collab_worker.set_active_session(sid)
            _ensure_sync_state(window)
            # Reconnect should not force snapshot replay if this session was already synced once,
            # otherwise unsent local edits can be wiped by older server state.
            if sid in window._collab_synced_sessions:
                return
            status, snap = window._collab_client().get_snapshot(sid)
            if status == 200 and isinstance(snap, dict):
                window.collab_snapshot_received.emit(snap)
                try:
                    window._collab_last_version_by_session[sid] = int(snap.get("version") or 0)
                except Exception:
                    window._collab_last_version_by_session[sid] = 0
                window._collab_synced_sessions.add(sid)

    window._collab_worker.connected.connect(_on_connected)
    window._collab_worker.disconnected.connect(lambda reason: window._append_system(f"Collab: {reason}"))
    window._collab_worker.connection_error.connect(lambda m: window._append_system(f"Collab error: {m}"))
    window._collab_worker.event_received.connect(window._on_collab_event_received)
    window._collab_worker.start()


def collab_client(window) -> CollabRestClient:
    base_url = window.edit_base_url.text().strip() or COLLAB_HTTP_BASE_DEFAULT
    return CollabRestClient(base_url=base_url, jwt_token=window._jwt)


def on_collab_refresh_sessions(window, silent: bool = False) -> None:
    if not window._jwt:
        if not silent:
            QMessageBox.warning(window, "Chat", "Load session and connect first.")
        return
    status, body = window._collab_client().list_sessions()
    window.combo_collab_sessions.clear()
    if status != 200:
        err_msg = body.get("message") or body.get("error") or body.get("raw") if isinstance(body, dict) else "Unknown error"
        if not silent:
            QMessageBox.warning(window, "Chat", f"Cannot load sessions (HTTP {status}).")
        window._append_system(f"Refresh sessions failed: HTTP {status} - {err_msg}")
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


def _session_entry_from_response(body: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    for key in ("item", "session", "data"):
        nested = body.get(key)
        if isinstance(nested, dict) and nested.get("sessionId"):
            return dict(nested)
    if body.get("sessionId"):
        return dict(body)
    return {}


def on_collab_create_session(window) -> None:
    if not window._jwt:
        QMessageBox.warning(window, "Chat", "Load session and connect first.")
        return

    img_path = ""
    if callable(window._current_image_path_fn):
        img_path = str(window._current_image_path_fn() or "").strip()
    image_stem = Path(img_path).stem.strip() if img_path else ""
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "projectId": f"proj_{suffix}",
        "imageId": image_stem or f"img_{suffix}",
        "cameraId": f"cam_{suffix}",
        "name": f"Session {datetime.now().strftime('%H:%M:%S')}",
    }

    status, body = window._collab_client().create_session(payload)
    if status not in (200, 201):
        message = body.get("message") if isinstance(body, dict) else ""
        raw = body.get("raw") if isinstance(body, dict) else ""
        details = message or raw or "unknown error"
        QMessageBox.warning(window, "Chat", f"Create session failed (HTTP {status}): {details}")
        window._append_system(f"Create session failed: HTTP {status} - {details}")
        return

    entry = _session_entry_from_response(body)
    sid = str(entry.get("sessionId") or "").strip()
    if not sid:
        QMessageBox.warning(window, "Chat", "Session created but response has no sessionId.")
        return

    name = str(entry.get("name") or sid)
    found_index = -1
    for i in range(window.combo_collab_sessions.count()):
        data = window.combo_collab_sessions.itemData(i)
        if isinstance(data, dict) and str(data.get("sessionId") or "").strip() == sid:
            found_index = i
            break
    if found_index < 0:
        if "version" not in entry:
            entry["version"] = 0
        window.combo_collab_sessions.addItem(f"{name} [{sid}]", entry)
        found_index = window.combo_collab_sessions.count() - 1

    window.combo_collab_sessions.setCurrentIndex(found_index)
    window._append_system(f"Created collab session: {name} [{sid}]")
    QMessageBox.information(window, "Chat", f"Session created: {sid}")


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
    _ensure_sync_state(window)
    status, snap = window._collab_client().get_snapshot(sid)
    if status == 200 and isinstance(snap, dict):
        try:
            window._collab_last_version_by_session[sid] = int(snap.get("version") or 0)
        except Exception:
            window._collab_last_version_by_session[sid] = 0
        window._collab_synced_sessions.add(sid)
        window.collab_snapshot_received.emit(snap)
        image_meta = snap.get("imageMeta")
        if not isinstance(image_meta, dict) or not image_meta.get("downloadUrl"):
            # If room has no published image yet, share local active image automatically.
            upload_current_image(window, show_message=False)
        send_collab_event(
            window,
            "session.user.joined",
            {
                "userId": str(window._user_id or ""),
                "displayName": str(window._user_id or "").split("@", 1)[0],
            },
        )
        QMessageBox.information(window, "Chat", f"Joined collaboration session: {sid}")
        window._append_system(f"Joined collab session: {sid}")
    else:
        err_msg = snap.get("message") or snap.get("error") or snap.get("raw") if isinstance(snap, dict) else "Unknown error"
        QMessageBox.warning(window, "Chat", f"Snapshot failed (HTTP {status}).\n{err_msg}")
        window._append_system(f"Snapshot failed: HTTP {status} - {err_msg}")


def on_collab_upload_image(window) -> None:
    upload_current_image(window, show_message=True)


def upload_current_image(window, show_message: bool = False) -> bool:
    if not window._collab_session:
        if show_message:
            QMessageBox.warning(window, "Chat", "Join a collaboration session first.")
        return False
    image_path = ""
    if callable(window._current_image_path_fn):
        image_path = str(window._current_image_path_fn() or "").strip()
    if not image_path:
        if show_message:
            QMessageBox.warning(window, "Chat", "No active image in project.")
        return False

    current_name = Path(image_path).stem.strip()
    image_id = current_name or str(window._collab_session.get("imageId") or f"img_{uuid.uuid4().hex[:8]}")
    window._collab_session["imageId"] = image_id
    status, body = window._collab_client().upload_temp_image(
        session_id=str(window._collab_session.get("sessionId") or ""),
        project_id=str(window._collab_session.get("projectId") or ""),
        image_id=image_id,
        camera_id=str(window._collab_session.get("cameraId") or ""),
        name=str(window._collab_session.get("name") or ""),
        file_path=image_path,
    )
    if status != 200 or not isinstance(body, dict):
        err_msg = body.get("message") or body.get("error") or body.get("raw") if isinstance(body, dict) else "Unknown error"
        if show_message:
            QMessageBox.warning(window, "Chat", f"Upload failed (HTTP {status}).\n{err_msg}")
        window._append_system(f"Upload image failed: HTTP {status} - {err_msg}")
        return False

    window._append_system(f"Uploaded image for collab: {body.get('fileName')}")
    window.send_collab_event(
        "image.available",
        {
            "sessionId": window._collab_session.get("sessionId"),
            "projectId": window._collab_session.get("projectId"),
            "imageId": body.get("imageId") or window._collab_session.get("imageId"),
            "cameraId": body.get("cameraId") or window._collab_session.get("cameraId"),
            "fileName": body.get("fileName"),
            "width": body.get("width"),
            "height": body.get("height"),
            "mimeType": body.get("mimeType"),
            "sizeBytes": body.get("sizeBytes"),
            "checksumSha256": body.get("checksumSha256"),
            "downloadUrl": body.get("downloadUrl"),
            "expiresAt": body.get("expiresAt"),
        },
    )
    if show_message:
        QMessageBox.information(window, "Chat", "Current image shared to collaboration session.")
    return True


def _image_ext_from_mime(content_type: str, file_name: str) -> str:
    guessed = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip().lower())
    if guessed:
        return guessed
    suffix = Path(file_name or "").suffix.strip()
    return suffix if suffix else ".jpg"


def download_image_from_event(window, envelope: dict) -> tuple[bool, str, str]:
    if not isinstance(envelope, dict):
        return False, "", "Invalid collab envelope."
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return False, "", "Invalid collab payload."

    image_id = str(payload.get("imageId") or envelope.get("imageId") or "").strip()
    if not image_id:
        return False, "", "Missing imageId in image.available payload."

    download_url = str(payload.get("downloadUrl") or "").strip()
    token = ""
    if download_url:
        try:
            token = (parse_qs(urlparse(download_url).query).get("token") or [""])[0]
        except Exception:
            token = ""
    if not token:
        return False, "", "Missing download token in image.available payload."

    status, data, content_type = window._collab_client().download_temp_image(image_id=image_id, token=token)
    if status != 200:
        return False, "", f"Image download failed (HTTP {status})."
    if not data:
        return False, "", "Server returned empty image payload."

    session_id = str(envelope.get("sessionId") or payload.get("sessionId") or "shared").strip() or "shared"
    base_name = str(payload.get("fileName") or image_id).strip() or image_id
    safe_base = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in base_name)
    ext = _image_ext_from_mime(content_type, safe_base)
    if not safe_base.lower().endswith(ext.lower()):
        safe_base = f"{safe_base}{ext}"

    collab_dir = Path(tempfile.gettempdir()) / "pyvisionannotator_collab" / session_id
    collab_dir.mkdir(parents=True, exist_ok=True)
    out_path = collab_dir / safe_base
    out_path.write_bytes(data)
    return True, str(out_path), ""


def send_collab_event(window, event_type: str, payload: dict[str, Any]) -> bool:
    if not window._collab_worker:
        window._append_system("Cannot sync now: not connected.")
        return False
    if not window._collab_session:
        window._append_system("Join a collaboration session first.")
        return False
    sid = str(window._collab_session.get("sessionId") or "").strip()
    if not sid:
        window._append_system("Cannot sync now: session is missing.")
        return False
    window._collab_version = max(0, int(window._collab_version)) + 1
    envelope = _build_event_envelope(window, str(event_type), payload, sid)

    if _maybe_send_chunked(window, envelope):
        if event_type.startswith("annotation."):
            action = event_type.split(".")[-1]
            label = payload.get("label", "") or "unlabeled"
            shape_type = payload.get("type", "shape")
            window._append_system(f"You {action}d {shape_type} '{label}'")
        return True

    window._collab_worker._seen_event_ids.add(envelope["eventId"])
    window._collab_worker.send_event(envelope)

    if event_type.startswith("annotation."):
        action = event_type.split(".")[-1]
        label = payload.get("label", "") or "unlabeled"
        shape_type = payload.get("type", "shape")
        window._append_system(f"You {action}d {shape_type} '{label}'")
        
    return True


def on_collab_event_received(window, payload: dict) -> None:
    _ensure_sync_state(window)
    event_id = str(payload.get("eventId") or "").strip()
    if event_id:
        if event_id in window._collab_processed_event_ids:
            return
        window._collab_processed_event_ids.add(event_id)
        if len(window._collab_processed_event_ids) > 4096:
            window._collab_processed_event_ids = set(list(window._collab_processed_event_ids)[-2048:])

    etype = str(payload.get("type") or "")
    ws_dest = str(payload.get("_wsDestination") or "").strip()

    if etype == "annotation.chunk":
        return
    if etype == "annotation.chunk.error":
        _handle_chunk_error(window, payload)
        return
    if etype == "annotation.chunk.ack":
        _handle_chunk_ack(window, payload)
        return

    if etype in ("session.created", "session.updated"):
        evt_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        session_obj = evt_payload.get("session") if isinstance(evt_payload.get("session"), dict) else None
        if not isinstance(session_obj, dict):
            session_obj = {
                "sessionId": payload.get("sessionId"),
                "projectId": payload.get("projectId"),
                "imageId": payload.get("imageId"),
                "cameraId": payload.get("cameraId"),
            }
        if "version" not in session_obj:
            session_obj["version"] = payload.get("version")
        _upsert_session_in_combo(window, session_obj)
        return

    # Only room-stream events should participate in per-session ordering gate.
    # Global /topic/sessions updates must not suppress room annotation events.
    is_room_stream = "/topic/sessions/" in ws_dest or etype.startswith("annotation.") or etype in (
        "image.available",
        "session.user.joined",
        "session.user.left",
    )
    if is_room_stream:
        sid = _session_id_from_event(payload)
        ver = _event_version(payload)
        if sid and ver > 0:
            last = int(window._collab_last_version_by_session.get(sid, 0))
            if ver <= last:
                return
            window._collab_last_version_by_session[sid] = ver

    if etype in ("session.user.joined", "session.user.left"):
        sid = _session_id_from_event(payload)
        actor = str(payload.get("actorId") or "someone")
        action = "joined" if etype.endswith("joined") else "left"
        window._append_system(f"{actor} {action} session {sid or ''}".strip())

    if etype.startswith("annotation."):
        action = etype.split(".")[-1]
        actor = payload.get("actorId", "Someone")
        data = payload.get("payload", {})
        label = data.get("label", "") or "unlabeled"
        shape_type = data.get("type", "shape")
        window._append_system(f"{actor} {action}d {shape_type} '{label}'")
        
        window.collab_event_received.emit(payload)
        return
    if etype == "image.available":
        ok, local_path, err = download_image_from_event(window, payload)
        if not ok:
            window._append_system(f"Collab image.available error: {err}")
            return
        evt_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        evt_payload["localPath"] = local_path
        payload["payload"] = evt_payload
        window._append_system(f"Collab image synced: {Path(local_path).name}")
        window.collab_event_received.emit(payload)
