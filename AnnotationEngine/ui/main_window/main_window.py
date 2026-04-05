"""
ui/main_window/main_window.py — MainWindow

Pure orchestrator: builds the three panels + canvas, wires their
outward signals together, and manages the remaining cross-cutting state
(_unsaved_changes, _ignore_changes, _load_process).
"""
from __future__ import annotations

import json
import shlex
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QStatusBar,
    QProgressDialog,
)

from core.annotation.annotation_manager import AnnotationManager
from core.workers.auth_worker import AuthWorker
from core.workers.autoseg_worker import AutoSegWorker as AutoSegYoloWorker
from core.workers.automask_worker import AutoMaskWorker
from ui.main_window.canvas import AnnotationCanvas
from ui.chat.chat_window import ChatWindow
from ui.main_window.panels.left_panel import LeftPanel
from ui.main_window.panels.toolbar_panel import ToolbarPanel
from ui.main_window.panels.right_panel import RightPanel
from utils.main_window_parts import (
    clear_unsaved,
    handle_close_event,
    load_process,
    on_automask_all_requested,
    on_autoseg_cancelled,
    on_autoseg_error,
    on_autoseg_requested,
    on_autoseg_result,
    on_autoseg_worker_finished,
    on_autoseg_yolo_cancelled,
    on_autoseg_yolo_error,
    on_autoseg_yolo_finished,
    on_autoseg_yolo_result,
    on_autoseg_yolo_run,
    on_data_changed,
    on_folder_opened,
    on_image_load_requested,
    on_image_loaded,
    on_auth_cancelled,
    on_auth_error,
    on_auth_finished,
    on_auth_requested,
    on_auth_success,
    build_collab_annotation_payload,
    is_empty_mask_annotation,
    normalize_collab_annotation_payload,
    on_save_before_switch,
    on_visual_settings_applied,
)


class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PyVisionAnnotator")
        self.resize(1500, 850)

        self._manager = AnnotationManager(self)
        self._unsaved_changes: bool = False
        self._ignore_changes: bool = False
        self._automask_worker: Optional[AutoMaskWorker] = None
        self._autoseg_worker: Optional[AutoSegYoloWorker] = None
        self._autoseg_progress: Optional[QProgressDialog] = None
        self._auth_worker: Optional[AuthWorker] = None
        self._auth_progress: Optional[QProgressDialog] = None
        self._auth_mode: str = "login"
        self._chat_window: Optional[ChatWindow] = None
        self._applying_remote_collab: bool = False
        self._collab_mask_update_timer: Optional[QTimer] = None
        self._pending_mask_update_ids: set[str] = set()

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    def _build_ui(self) -> None:
        self._canvas = AnnotationCanvas(self._manager, self)

        self._left = LeftPanel(
            current_image_path_fn=lambda: self._manager.image_path,
            unsaved_fn=lambda: self._unsaved_changes,
            parent=self,
        )
        self._right = RightPanel(
            manager=self._manager,
            canvas_fn=lambda: self._canvas,
            parent=self,
        )
        self._toolbar = ToolbarPanel(
            manager=self._manager,
            folder_path_fn=lambda: self._left.folder_path,
            parent=self,
        )
        self.addToolBar(self._toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._left)
        splitter.addWidget(self._canvas)
        splitter.addWidget(self._right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([220, 900, 280])
        self.setCentralWidget(splitter)

        self._status = QStatusBar(self)
        self.setStatusBar(self._status)
        self._status.showMessage("Ready - open a folder to begin.")

    def _connect_signals(self) -> None:
        self._left.folder_opened.connect(self._on_folder_opened)
        self._left.image_load_requested.connect(self._on_image_load_requested)
        self._left.save_before_switch_requested.connect(self._on_save_before_switch)

        self._toolbar.status_message.connect(self._status.showMessage)
        self._toolbar.unsaved_cleared.connect(self._clear_unsaved)
        self._toolbar.annotations_loaded.connect(self._load_process)
        self._toolbar.settings_applied.connect(self._on_visual_settings_applied)
        self._toolbar.auth_requested.connect(self._on_auth_requested)
        self._toolbar.chat_requested.connect(self._on_chat_requested)

        self._right.status_message.connect(self._status.showMessage)
        self._right.tool_changed.connect(self._canvas.set_tool)
        self._right.brush_size_changed.connect(self._canvas.set_brush_size)
        self._right.crosshair_toggled.connect(self._canvas.set_crosshair)
        self._right.canvas_brightness.connect(self._canvas.set_brightness)
        self._right.canvas_contrast.connect(self._canvas.set_contrast)
        self._right.canvas_gamma.connect(self._canvas.set_gamma)
        self._right.mask_opacity_changed.connect(self._manager.set_mask_opacity)
        self._right.autoseg_run_requested.connect(self._on_autoseg_yolo_run)
        self._right.automask_all_requested.connect(self._on_automask_all_requested)

        self._canvas.image_loaded.connect(self._on_image_loaded)
        self._canvas.scene().selectionChanged.connect(self._right.on_scene_selection_changed)
        self._canvas.autoseg_requested.connect(self._on_autoseg_requested)

        self._manager.annotation_added.connect(self._on_data_changed)
        self._manager.annotation_removed.connect(self._on_data_changed)
        self._manager.annotation_updated.connect(self._on_data_changed)
        self._manager.annotations_cleared.connect(self._on_data_changed)
        self._manager.annotation_added.connect(self._on_collab_annotation_added)
        self._manager.annotation_removed.connect(self._on_collab_annotation_removed)
        self._manager.annotation_updated.connect(self._on_collab_annotation_updated)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Delete"), self).activated.connect(self._canvas.delete_selected)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._left.btn_open_folder.click)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._toolbar.save_json)

    @staticmethod
    def _parse_custom_args(raw: object) -> list[str]:
        text = str(raw or "").strip()
        if not text:
            return []
        try:
            return shlex.split(text, posix=False)
        except ValueError:
            return text.split()

    @staticmethod
    def _normalize_collab_annotation_payload(payload: dict) -> dict:
        return normalize_collab_annotation_payload(payload)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._flush_pending_mask_updates()
        handle_close_event(self, event)

    def _on_data_changed(self, *_args) -> None:
        on_data_changed(self, *_args)

    def _clear_unsaved(self) -> None:
        clear_unsaved(self)

    def _on_folder_opened(self, folder: str) -> None:
        on_folder_opened(self, folder)

    def _on_image_load_requested(self, path: str) -> None:
        on_image_load_requested(self, path)

    def _on_save_before_switch(self) -> None:
        on_save_before_switch(self)

    def _on_image_loaded(self, path: str, w: int, h: int) -> None:
        on_image_loaded(self, path, w, h)
        self._sync_collab_current_image_if_needed()

    def _on_visual_settings_applied(self, pen_width: int, font_size: int, label_height: int) -> None:
        on_visual_settings_applied(self, pen_width, font_size, label_height)

    def _on_auth_requested(self) -> None:
        on_auth_requested(self)

    def _on_auth_success(self, payload: dict) -> None:
        on_auth_success(self, payload)

    def _on_auth_error(self, message: str) -> None:
        on_auth_error(self, message)

    def _on_auth_cancelled(self) -> None:
        on_auth_cancelled(self)

    def _on_auth_finished(self) -> None:
        on_auth_finished(self)

    def _on_chat_requested(self) -> None:
        if self._chat_window is None:
            self._chat_window = ChatWindow(current_image_path_fn=lambda: self._manager.image_path)
            self._chat_window.collab_snapshot_received.connect(self._on_collab_snapshot_received)
            self._chat_window.collab_event_received.connect(self._on_collab_event_received)
        self._chat_window.show()
        self._chat_window.raise_()
        self._chat_window.activateWindow()

    def _on_collab_snapshot_received(self, snapshot: dict) -> None:
        if not isinstance(snapshot, dict):
            return
        self._load_collab_snapshot_image(snapshot)
        anns = snapshot.get("annotations") if isinstance(snapshot.get("annotations"), list) else []
        normalized_anns: list[dict] = []
        for ann in anns:
            if isinstance(ann, dict):
                normalized = self._normalize_collab_annotation_payload(ann)
                if is_empty_mask_annotation(normalized):
                    continue
                normalized_anns.append(normalized)
        self._applying_remote_collab = True
        try:
            for item in self._manager.clear():
                self._canvas.scene().removeItem(item)
            items = self._manager.load_annotations(normalized_anns)
            for item in items:
                self._canvas.add_annotation_item(item)
        finally:
            self._applying_remote_collab = False

    def _on_collab_event_received(self, envelope: dict) -> None:
        if not isinstance(envelope, dict):
            return
        
        # STOMP worker's `_seen_event_ids` deduplicates our own messages.
        # Dropping by `actorId` prevents testing with 2 clients on the same account.
        
        etype = str(envelope.get("type") or "")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            return
        payload = self._normalize_collab_annotation_payload(payload)
        if self._chat_window and etype.startswith("annotation."):
            try:
                payload_json = json.dumps(payload, separators=(",", ":"))
            except Exception:
                payload_json = str(payload)
            self._chat_window._append_system(
                f"[collab] incoming {etype} payloadJson={payload_json}"
            )
        if etype == "image.available":
            self._load_collab_image_event(envelope)
            return

        self._applying_remote_collab = True
        try:
            if etype in ("annotation.create", "annotation.update"):
                ann_id = str(payload.get("id") or "").strip()

                # Ignore non-drawable masks (missing or empty points after normalization).
                if is_empty_mask_annotation(payload):
                    if self._chat_window:
                        self._chat_window._append_system(
                            f"[collab] ignored {etype} for mask id={ann_id or '?'} (empty points)"
                        )
                    return

                # Replace existing item first so manager keeps the incoming item,
                # not a transient one removed right after creation.
                if ann_id:
                    existing = self._manager.remove(ann_id)
                    if existing is not None:
                        self._canvas.scene().removeItem(existing)

                created = self._manager.load_annotations([payload])
                if not created:
                    return

                for item in created:
                    self._canvas.add_annotation_item(item)
            elif etype == "annotation.delete":
                ann_id = str(payload.get("id") or "").strip()
                if ann_id:
                    removed = self._manager.remove(ann_id)
                    if removed is not None:
                        self._canvas.scene().removeItem(removed)
        finally:
            self._applying_remote_collab = False

    def _load_collab_snapshot_image(self, snapshot: dict) -> None:
        if not self._chat_window:
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
        self._load_collab_image_event(envelope)

    def _load_collab_image_event(self, envelope: dict) -> None:
        if not self._chat_window:
            return
        ok, image_path, err = self._chat_window.download_collab_image(envelope)
        if not ok:
            self._status.showMessage(err)
            return
        self._applying_remote_collab = True
        self._ignore_changes = True
        try:
            self._canvas.load_image(image_path)
        finally:
            self._ignore_changes = False
            self._applying_remote_collab = False
        self._unsaved_changes = False
        self._status.showMessage(f"Collab image synced: {image_path}")

    def _sync_collab_current_image_if_needed(self) -> None:
        if self._applying_remote_collab or not self._chat_window:
            return
        self._chat_window.upload_current_collab_image(show_message=False)

    def _build_collab_annotation_payload(self, event_type: str, ann_id: str) -> dict | None:
        return build_collab_annotation_payload(self._manager, event_type, ann_id)

    def _emit_collab_annotation(self, event_type: str, annotation_id: str) -> None:
        if self._applying_remote_collab:
            return
        if not self._chat_window:
            return
        ann_id = str(annotation_id or "").strip()
        if not ann_id:
            return
        payload = self._build_collab_annotation_payload(event_type, ann_id)
        if payload is None:
            if self._chat_window:
                self._chat_window._append_system(
                    f"[collab] payload build failed for {event_type} id={ann_id}"
                )
            return
        try:
            payload_json = json.dumps(payload, separators=(",", ":"))
        except Exception:
            payload_json = str(payload)
        self._chat_window._append_system(
            f"[collab] local emit {event_type} id={ann_id} payloadJson={payload_json}"
        )
        sent = self._chat_window.send_collab_event(event_type, payload)
        if not sent:
            self._chat_window._append_system(
                f"[collab] send blocked for {event_type} id={ann_id}"
            )

    def _schedule_mask_update_emit(self, annotation_id: str) -> None:
        ann_id = str(annotation_id or "").strip()
        if not ann_id:
            return
        self._pending_mask_update_ids.add(ann_id)
        if self._collab_mask_update_timer is None:
            self._collab_mask_update_timer = QTimer(self)
            self._collab_mask_update_timer.setSingleShot(True)
            self._collab_mask_update_timer.timeout.connect(self._flush_pending_mask_updates)
        # Send mask updates after brush activity settles to avoid redundant WS traffic.
        self._collab_mask_update_timer.start(220)

    def _flush_pending_mask_updates(self) -> None:
        if not self._pending_mask_update_ids:
            return
        pending_ids = list(self._pending_mask_update_ids)
        self._pending_mask_update_ids.clear()
        for ann_id in pending_ids:
            self._emit_collab_annotation("annotation.update", ann_id)

    def _on_collab_annotation_added(self, annotation_id: str) -> None:
        self._emit_collab_annotation("annotation.create", annotation_id)

    def _on_collab_annotation_removed(self, annotation_id: str) -> None:
        self._pending_mask_update_ids.discard(str(annotation_id or "").strip())
        self._emit_collab_annotation("annotation.delete", annotation_id)

    def _on_collab_annotation_updated(self, annotation_id: str) -> None:
        ann_id = str(annotation_id or "").strip()
        if not ann_id:
            return
        item = self._manager.get(ann_id)
        if item is None:
            return
        payload = item.to_dict() if hasattr(item, "to_dict") else {}
        atype = str(payload.get("type") or "") if isinstance(payload, dict) else ""
        if atype == "mask":
            self._schedule_mask_update_emit(ann_id)
            return
        self._emit_collab_annotation("annotation.update", ann_id)

    def _load_process(self, image_path: str, annotations: list) -> None:
        load_process(self, image_path, annotations)

    def _on_autoseg_config(self) -> None:
        pass

    def _on_autoseg_requested(self, scene_pos) -> None:
        on_autoseg_requested(self, scene_pos)

    def _on_autoseg_result(self, data: dict | list) -> None:
        on_autoseg_result(self, data)

    def _on_automask_all_requested(self) -> None:
        on_automask_all_requested(self)

    def _on_autoseg_error(self, message: str) -> None:
        on_autoseg_error(self, message)

    def _on_autoseg_cancelled(self) -> None:
        on_autoseg_cancelled(self)

    def _on_autoseg_worker_finished(self) -> None:
        on_autoseg_worker_finished(self)

    def _on_autoseg_yolo_run(self) -> None:
        on_autoseg_yolo_run(self)

    def _on_autoseg_yolo_result(self, detections: list) -> None:
        on_autoseg_yolo_result(self, detections)

    def _on_autoseg_yolo_error(self, message: str) -> None:
        on_autoseg_yolo_error(self, message)

    def _on_autoseg_yolo_cancelled(self) -> None:
        on_autoseg_yolo_cancelled(self)

    def _on_autoseg_yolo_finished(self) -> None:
        on_autoseg_yolo_finished(self)

