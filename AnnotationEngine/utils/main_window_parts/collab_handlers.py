"""Collaboration event handlers extracted from MainWindow.

Inbound: snapshot/event receive, image sync, annotation create/update/delete with payload normalization.
Outbound: emit local changes (deduped masks via timer). Key: on_collab_snapshot_received,
on_collab_event_received, emit_collab_annotation, schedule_mask_update_emit, sync_collab_current_image_if_needed.
"""
from __future__ import annotations

from PyQt6.QtCore import QTimer

from ui.chat.chat_window import ChatWindow

from .collab_payload import (
    build_collab_annotation_payload,
    is_empty_mask_annotation,
    normalize_collab_annotation_payload,
)


def on_chat_requested(window) -> None:
    if window._chat_window is None:
        window._chat_window = ChatWindow(current_image_path_fn=lambda: window._manager.image_path)
        window._chat_window.collab_snapshot_received.connect(window._on_collab_snapshot_received)
        window._chat_window.collab_event_received.connect(window._on_collab_event_received)
    window._chat_window.show()
    window._chat_window.raise_()
    window._chat_window.activateWindow()


def on_collab_snapshot_received(window, snapshot: dict) -> None:
    if not isinstance(snapshot, dict):
        return
    load_collab_snapshot_image(window, snapshot)

    anns = snapshot.get("annotations") if isinstance(snapshot.get("annotations"), list) else []
    normalized_anns: list[dict] = []
    for ann in anns:
        if not isinstance(ann, dict):
            continue
        normalized = normalize_collab_annotation_payload(ann)
        if is_empty_mask_annotation(normalized):
            continue
        normalized_anns.append(normalized)

    window._applying_remote_collab = True
    try:
        for item in window._manager.clear():
            window._canvas.scene().removeItem(item)
        items = window._manager.load_annotations(normalized_anns)
        for item in items:
            window._canvas.add_annotation_item(item)
    finally:
        window._applying_remote_collab = False


def on_collab_event_received(window, envelope: dict) -> None:
    if not isinstance(envelope, dict):
        return

    etype = str(envelope.get("type") or "")
    if etype == "image.available":
        load_collab_image_event(window, envelope)
        return

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return
    payload = normalize_collab_annotation_payload(payload)

    if window._chat_window and etype.startswith("annotation."):
        ann_id = str(payload.get("id") or "?").strip() or "?"
        ann_type = str(payload.get("type") or "shape")
        label = str(payload.get("label") or "unlabeled")
        window._chat_window._append_system(
            f"[collab] incoming {etype} id={ann_id} type={ann_type} label='{label}'"
        )

    window._applying_remote_collab = True
    try:
        if etype in ("annotation.create", "annotation.update"):
            ann_id = str(payload.get("id") or "").strip()
            if is_empty_mask_annotation(payload):
                if window._chat_window:
                    window._chat_window._append_system(
                        f"[collab] ignored {etype} for mask id={ann_id or '?'} (empty points)"
                    )
                return

            if ann_id:
                existing = window._manager.remove(ann_id)
                if existing is not None:
                    window._canvas.scene().removeItem(existing)

            created = window._manager.load_annotations([payload])
            if not created:
                return
            for item in created:
                window._canvas.add_annotation_item(item)

        elif etype == "annotation.delete":
            ann_id = str(payload.get("id") or "").strip()
            if ann_id:
                removed = window._manager.remove(ann_id)
                if removed is not None:
                    window._canvas.scene().removeItem(removed)
    finally:
        window._applying_remote_collab = False


def load_collab_snapshot_image(window, snapshot: dict) -> None:
    if not window._chat_window:
        return
    image_meta = snapshot.get("imageMeta")
    if not isinstance(image_meta, dict):
        return
    envelope = {
        "type": "image.available",
        "sessionId": snapshot.get("sessionId"),
        "imageId": snapshot.get("imageId"),
        "payload": {
            "imageId": image_meta.get("imageId") or snapshot.get("imageId"),
            "downloadUrl": image_meta.get("downloadUrl"),
            "fileName": image_meta.get("fileName") or image_meta.get("name") or snapshot.get("imageId"),
            "sessionId": snapshot.get("sessionId"),
        },
    }
    load_collab_image_event(window, envelope)


def load_collab_image_event(window, envelope: dict) -> None:
    if not window._chat_window:
        return
    ok, image_path, err = window._chat_window.download_collab_image(envelope)
    if not ok:
        window._status.showMessage(err)
        return

    window._applying_remote_collab = True
    window._ignore_changes = True
    try:
        window._canvas.load_image(image_path)
    finally:
        window._ignore_changes = False
        window._applying_remote_collab = False

    window._unsaved_changes = False
    window._status.showMessage(f"Collab image synced: {image_path}")


def sync_collab_current_image_if_needed(window) -> None:
    if window._applying_remote_collab or not window._chat_window:
        return
    window._chat_window.upload_current_collab_image(show_message=False)


def emit_collab_annotation(window, event_type: str, annotation_id: str) -> None:
    if window._applying_remote_collab or not window._chat_window:
        return

    ann_id = str(annotation_id or "").strip()
    if not ann_id:
        return

    payload = build_collab_annotation_payload(window._manager, event_type, ann_id)
    if payload is None:
        window._chat_window._append_system(
            f"[collab] payload build failed for {event_type} id={ann_id}"
        )
        return

    ann_type = str(payload.get("type") or "shape")
    label = str(payload.get("label") or "unlabeled")
    window._chat_window._append_system(
        f"[collab] queued {event_type} id={ann_id} type={ann_type} label='{label}'"
    )

    sent = window._chat_window.send_collab_event(event_type, payload)
    if not sent:
        window._chat_window._append_system(
            f"[collab] send blocked for {event_type} id={ann_id}"
        )


def schedule_mask_update_emit(window, annotation_id: str) -> None:
    ann_id = str(annotation_id or "").strip()
    if not ann_id:
        return
    window._pending_mask_update_ids.add(ann_id)
    if window._collab_mask_update_timer is None:
        window._collab_mask_update_timer = QTimer(window)
        window._collab_mask_update_timer.setSingleShot(True)
        window._collab_mask_update_timer.timeout.connect(window._flush_pending_mask_updates)
    # Send mask updates after brush activity settles to avoid redundant WS traffic.
    window._collab_mask_update_timer.start(220)


def flush_pending_mask_updates(window) -> None:
    if not window._pending_mask_update_ids:
        return
    pending_ids = list(window._pending_mask_update_ids)
    window._pending_mask_update_ids.clear()
    for ann_id in pending_ids:
        emit_collab_annotation(window, "annotation.update", ann_id)


def on_collab_annotation_added(window, annotation_id: str) -> None:
    emit_collab_annotation(window, "annotation.create", annotation_id)


def on_collab_annotation_removed(window, annotation_id: str) -> None:
    window._pending_mask_update_ids.discard(str(annotation_id or "").strip())
    emit_collab_annotation(window, "annotation.delete", annotation_id)


def on_collab_annotation_updated(window, annotation_id: str) -> None:
    ann_id = str(annotation_id or "").strip()
    if not ann_id:
        return

    item = window._manager.get(ann_id)
    if item is None:
        return

    payload = item.to_dict() if hasattr(item, "to_dict") else {}
    atype = str(payload.get("type") or "") if isinstance(payload, dict) else ""
    if atype == "mask":
        schedule_mask_update_emit(window, ann_id)
        return

    emit_collab_annotation(window, "annotation.update", ann_id)
