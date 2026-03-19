"""
ui/main_window.py — MainWindow

Pure orchestrator: builds the three panels + canvas, wires their
outward signals together, and manages the remaining cross-cutting state
(_unsaved_changes, _ignore_changes, _load_process).
"""
from __future__ import annotations

import shlex
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QStatusBar,
    QProgressDialog,
)

from core.annotation_manager import AnnotationManager
from core.autoseg_worker import AutoSegWorker as AutoSegYoloWorker
from core.automask_worker import AutoMaskWorker
from ui.canvas import AnnotationCanvas
from ui.panels.left_panel import LeftPanel
from ui.panels.toolbar_panel import ToolbarPanel
from ui.panels.right_panel import RightPanel
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
        self._toolbar.settings_applied.connect(self._on_visual_settings_applied)

        # ---- Right panel ----
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

    @staticmethod
    def _parse_custom_args(raw: object) -> list[str]:
        """Parse user-entered CLI args into a safe argument list."""
        text = str(raw or "").strip()
        if not text:
            return []
        try:
            return shlex.split(text, posix=False)
        except ValueError:
            # Fallback: split by whitespace if quoting is malformed.
            return text.split()

    def closeEvent(self, event: QCloseEvent) -> None:
        handle_close_event(self, event)

    # ================================================================== #
    #  Slots
    # ================================================================== #
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

    def _on_visual_settings_applied(self, pen_width: int, font_size: int, label_height: int) -> None:
        on_visual_settings_applied(self, pen_width, font_size, label_height)

    # ================================================================== #
    #  Import / load-process  (cross-cutting: touches canvas + left panel)
    # ================================================================== #
    def _load_process(self, image_path: str, annotations: list) -> None:
        load_process(self, image_path, annotations)

    # ================================================================== #
    #  AutoSeg integration
    # ================================================================== #
    def _on_autoseg_config(self) -> None:
        """Open the AutoSeg settings dialog (Merged into main Settings)."""
        # This slot is no longer called by toolbar, but might be called if we didn't fully clean up.
        # The toolbar now handles its own settings dialog which includes AutoSeg.
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

    # ================================================================== #
    #  AutoSeg (YOLO) integration
    # ================================================================== #
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

