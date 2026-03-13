"""
ui/main_window.py — MainWindow

Pure orchestrator: builds the three panels + canvas, wires their
outward signals together, and manages the remaining cross-cutting state
(_unsaved_changes, _ignore_changes, _load_process).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QStatusBar,
    QMessageBox,
    QProgressDialog,
)

from core.annotation_manager import AnnotationManager
from core.autoseg_worker import AutoSegWorker
from ui.canvas import AnnotationCanvas
from ui.panels.left_panel import LeftPanel
from ui.panels.toolbar_panel import ToolbarPanel
from ui.panels.right_panel import RightPanel


class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PyVisionAnnotator")
        self.resize(1500, 850)

        self._manager = AnnotationManager(self)
        self._unsaved_changes: bool = False
        self._ignore_changes: bool = False
        self._autoseg_worker: Optional[AutoSegWorker] = None
        self._autoseg_progress: Optional[QProgressDialog] = None

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    # ================================================================== #
    #  UI construction
    # ================================================================== #
    def _build_ui(self) -> None:
        # Canvas (created first so panels can hold a lazy reference to it)
        self._canvas = AnnotationCanvas(self._manager, self)

        # Panels — each gets the dependencies it needs via callables
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
        self._status.showMessage("Ready — open a folder to begin.")

    # ================================================================== #
    #  Signal wiring
    # ================================================================== #
    def _connect_signals(self) -> None:
        # ---- Left panel ----
        self._left.folder_opened.connect(self._on_folder_opened)
        self._left.image_load_requested.connect(self._on_image_load_requested)
        self._left.save_before_switch_requested.connect(self._on_save_before_switch)

        # ---- Toolbar panel ----
        self._toolbar.status_message.connect(self._status.showMessage)
        self._toolbar.unsaved_cleared.connect(self._clear_unsaved)
        self._toolbar.annotations_loaded.connect(self._load_process)

        # ---- Right panel ----
        self._right.status_message.connect(self._status.showMessage)
        self._right.tool_changed.connect(self._canvas.set_tool)
        self._right.brush_size_changed.connect(self._canvas.set_brush_size)
        self._right.crosshair_toggled.connect(self._canvas.set_crosshair)
        self._right.canvas_brightness.connect(self._canvas.set_brightness)
        self._right.canvas_contrast.connect(self._canvas.set_contrast)
        self._right.canvas_gamma.connect(self._canvas.set_gamma)

        # ---- Canvas ----
        self._canvas.image_loaded.connect(self._on_image_loaded)
        self._canvas.scene().selectionChanged.connect(self._right.on_scene_selection_changed)
        self._canvas.autoseg_requested.connect(self._on_autoseg_requested)

        # ---- Dirty tracking (manager → MainWindow) ----
        self._manager.annotation_added.connect(self._on_data_changed)
        self._manager.annotation_removed.connect(self._on_data_changed)
        self._manager.annotation_updated.connect(self._on_data_changed)
        self._manager.annotations_cleared.connect(self._on_data_changed)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Delete"), self).activated.connect(self._canvas.delete_selected)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._left.btn_open_folder.click)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._toolbar.save_json)

    # ================================================================== #
    #  Slots
    # ================================================================== #
    def _on_data_changed(self, *_args) -> None:
        if not self._ignore_changes:
            self._unsaved_changes = True

    def _clear_unsaved(self) -> None:
        self._unsaved_changes = False

    def _on_folder_opened(self, folder: str) -> None:
        self._toolbar.reset_export_root()
        self._status.showMessage(f"Loaded {self._left.file_list.count()} image(s) from {folder}")

    def _on_image_load_requested(self, path: str) -> None:
        """Left panel wants to load a new image."""
        self._ignore_changes = True
        self._canvas.load_image(path)
        self._ignore_changes = False
        self._unsaved_changes = False

    def _on_save_before_switch(self) -> None:
        """Left panel deferred a switch — we must save first."""
        if self._toolbar.save_json():
            self._left.confirm_switch()
        else:
            self._left.cancel_switch()

    def _on_image_loaded(self, path: str, w: int, h: int) -> None:
        self._status.showMessage(f"{Path(path).name}  ({w} × {h} px)")

    # ================================================================== #
    #  Import / load-process  (cross-cutting: touches canvas + left panel)
    # ================================================================== #
    def _load_process(self, image_path: str, annotations: list) -> None:
        """Called by toolbar after a successful JSON/CSV import."""
        current_norm = os.path.normcase(os.path.abspath(self._manager.image_path or ""))
        new_norm     = os.path.normcase(os.path.abspath(image_path or ""))

        if image_path and new_norm != current_norm:
            self._ignore_changes = True
            self._canvas.load_image(image_path)
            self._ignore_changes = False
        else:
            # Same image — clear existing annotations first (no duplicates)
            self._ignore_changes = True
            for old in self._manager.clear():
                self._canvas.scene().removeItem(old)
            self._ignore_changes = False

        self._ignore_changes = True
        items = self._manager.load_annotations(annotations)
        for item in items:
            self._canvas.add_annotation_item(item)
        self._ignore_changes = False

        if image_path:
            self._left.select_item_for_path(image_path)

        self._unsaved_changes = False
        self._status.showMessage(f"Loaded {len(items)} annotation(s).")

    # ================================================================== #
    #  AutoSeg integration
    # ================================================================== #
    def _on_autoseg_config(self) -> None:
        """Open the AutoSeg settings dialog (Merged into main Settings)."""
        # This slot is no longer called by toolbar, but might be called if we didn't fully clean up.
        # The toolbar now handles its own settings dialog which includes AutoSeg.
        pass

    def _on_autoseg_requested(self, scene_pos) -> None:
        """Canvas emitted an AutoSeg click — launch the segmentation subprocess."""
        from PyQt6.QtCore import QSettings
        settings = QSettings("PyVisionAnnotator", "PyVisionAnnotator")
        exe = settings.value("autoseg/model_path", "")
        timeout = int(settings.value("autoseg/timeout", 120))
        # script is always None as we run executable directly
        script = None

        if not exe:
            self._canvas.autoseg_error_received("AutoSeg not configured.")
            self._status.showMessage("AutoMask not configured — open Settings first.")
            return

        image_path = self._manager.image_path
        if not image_path:
            self._canvas.autoseg_error_received("No image loaded.")
            return

        px = int(round(scene_pos.x()))
        py = int(round(scene_pos.y()))

        self._status.showMessage(f"AutoMask: segmenting at ({px}, {py}) — please wait …")

        # Progress dialog (indeterminate)
        self._autoseg_progress = QProgressDialog(
            "Running segmentation model …", "Cancel", 0, 0, self
        )
        self._autoseg_progress.setWindowTitle("AutoMask")
        self._autoseg_progress.setMinimumDuration(0)
        self._autoseg_progress.canceled.connect(self._on_autoseg_cancelled)
        self._autoseg_progress.show()

        # Launch worker thread
        self._autoseg_worker = AutoSegWorker(
            executable=exe,
            script=script,
            image_path=image_path,
            point_x=px,
            point_y=py,
            timeout=timeout,
            parent=self,
        )
        self._autoseg_worker.result_ready.connect(self._on_autoseg_result)
        self._autoseg_worker.error_occurred.connect(self._on_autoseg_error)
        self._autoseg_worker.finished.connect(self._on_autoseg_worker_finished)
        self._autoseg_worker.start()

    def _on_autoseg_result(self, data: dict) -> None:
        """AutoSegWorker succeeded — forward result to canvas."""
        label = data.get("label", "")
        n_pts = len(data.get("coordinates", []))
        self._status.showMessage(
            f"AutoMask: segmented \"{label}\" — {n_pts} boundary points → mask created."
        )
        self._canvas.autoseg_result_received(data)

    def _on_autoseg_error(self, message: str) -> None:
        """AutoSegWorker failed."""
        self._canvas.autoseg_error_received(message)
        self._status.showMessage("AutoMask: segmentation failed.")
        QMessageBox.warning(self, "AutoMask Error", message)

    def _on_autoseg_cancelled(self) -> None:
        """User pressed Cancel on the progress dialog."""
        if self._autoseg_worker and self._autoseg_worker.isRunning():
            self._autoseg_worker.cancel()       # kill the OS process
            self._autoseg_worker.wait(3000)     # wait for thread to exit naturally
        self._canvas._autoseg_reset()
        self._status.showMessage("AutoMask: cancelled.")

    def _on_autoseg_worker_finished(self) -> None:
        """Clean up progress dialog when the worker thread finishes."""
        if self._autoseg_progress:
            self._autoseg_progress.close()
            self._autoseg_progress = None
        self._autoseg_worker = None
