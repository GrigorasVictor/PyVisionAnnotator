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

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QKeySequence, QShortcut, QPolygonF
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QStatusBar,
    QMessageBox,
    QProgressDialog,
)

from core.annotation_manager import AnnotationManager
from core.autoseg_worker import AutoSegWorker as AutoSegYoloWorker
from core.automask_worker import AutoMaskWorker
from ui.canvas import AnnotationCanvas
from ui.panels.left_panel import LeftPanel
from ui.panels.toolbar_panel import ToolbarPanel
from ui.panels.right_panel import RightPanel
from ui.autoseg_run_dialog import AutoSegRunDialog


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

        # ---- Right panel ----
        self._right.status_message.connect(self._status.showMessage)
        self._right.tool_changed.connect(self._canvas.set_tool)
        self._right.brush_size_changed.connect(self._canvas.set_brush_size)
        self._right.crosshair_toggled.connect(self._canvas.set_crosshair)
        self._right.canvas_brightness.connect(self._canvas.set_brightness)
        self._right.canvas_contrast.connect(self._canvas.set_contrast)
        self._right.canvas_gamma.connect(self._canvas.set_gamma)
        self._right.autoseg_run_requested.connect(self._on_autoseg_yolo_run)

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
        self._automask_worker = AutoMaskWorker(
            executable=exe,
            script=script,
            image_path=image_path,
            point_x=px,
            point_y=py,
            timeout=timeout,
            parent=self,
        )
        self._automask_worker.result_ready.connect(self._on_autoseg_result)
        self._automask_worker.error_occurred.connect(self._on_autoseg_error)
        self._automask_worker.finished.connect(self._on_autoseg_worker_finished)
        self._automask_worker.start()

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
        if self._automask_worker and self._automask_worker.isRunning():
            self._automask_worker.cancel()       # kill the OS process
            self._automask_worker.wait(3000)     # wait for thread to exit naturally
        self._canvas._autoseg_reset()
        self._status.showMessage("AutoMask: cancelled.")

    def _on_autoseg_worker_finished(self) -> None:
        """Clean up progress dialog when the worker thread finishes."""
        if self._autoseg_progress:
            self._autoseg_progress.close()
            self._autoseg_progress = None
        self._automask_worker = None

    # ================================================================== #
    #  AutoSeg (YOLO) integration
    # ================================================================== #
    def _on_autoseg_yolo_run(self) -> None:
        """Run YOLO segmentation on the full image."""
        from PyQt6.QtCore import QSettings
        settings = QSettings("PyVisionAnnotator", "PyVisionAnnotator")

        # Use configured executable, no python script wrapper
        executable = settings.value("autoseg_yolo/executable", "")
        # If blank, fallback? Or warn?
        
        image_path = self._manager.image_path
        if not image_path:
             QMessageBox.warning(self, "No Image", "Please load an image first.")
             return
             
        # Optional weights path (e.g. .pt file) if the executable requires it
        model_path = settings.value("autoseg_yolo/model_path", "")
        conf = float(settings.value("autoseg_yolo/conf", 0.32))
        device = settings.value("autoseg_yolo/device", "cpu")

        if not executable:
             QMessageBox.warning(self, "Not Configured", "Please set the YOLO Executable path in Settings.")
             return

        # Prompt for labels and mode
        dlg = AutoSegRunDialog(self)
        if not dlg.exec():
            return
            
        labels, mode = dlg.get_values()
        
        if not labels:
            QMessageBox.warning(self, "No Labels", "Please enter at least one label.")
            return
            
        if not mode:
            QMessageBox.warning(self, "No Mode", "Please select at least one output mode (BBox or Segment).")
            return

        self._status.showMessage("Running AutoSeg (YOLO)...")
        
        self._autoseg_progress = QProgressDialog(
            "Running YOLO segmentation...", "Cancel", 0, 0, self
        )
        self._autoseg_progress.setWindowTitle("AutoSeg (YOLO)")
        self._autoseg_progress.setMinimumDuration(0)
        self._autoseg_progress.canceled.connect(self._on_autoseg_yolo_cancelled)
        self._autoseg_progress.show()
        
        self._autoseg_worker = AutoSegYoloWorker(
            executable=executable,
            script=None,  # No script, running exe directly
            image_path=image_path,
            labels=labels,
            conf_threshold=conf,
            device=device,
            mode=mode, # Pass the selected mode(s)
            parent=self
        )
        self._autoseg_worker.result_ready.connect(self._on_autoseg_yolo_result)
        self._autoseg_worker.error_occurred.connect(self._on_autoseg_yolo_error)
        self._autoseg_worker.finished.connect(self._on_autoseg_yolo_finished)
        self._autoseg_worker.start()

    def _add_polygon(self, coords: list, label: str) -> None:
        """Helper to convert [ [x,y], ... ] into a vector PolygonItem (visual figure)."""
        poly = QPolygonF()
        for p in coords:
            if isinstance(p, list) and len(p) >= 2:
                poly.append(QPointF(float(p[0]), float(p[1])))
        
        if not poly.isEmpty():
            item = self._manager.add_poly(poly, label=label, color=self._manager.default_color)
            self._canvas.add_annotation_item(item)

    def _on_autoseg_yolo_result(self, detections: list) -> None:
        """Process results from YOLO."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"AutoSeg received {len(detections)} detections: {detections}")

        count = 0
        self._ignore_changes = True
        for det in detections:
            label = det.get("label", "Object")
            
            # 1. Coordinates -> Polygon (Vector figure)
            if "coordinates" in det:
                 coords = det["coordinates"]
                 if isinstance(coords, list) and len(coords) > 2:
                     self._add_polygon(coords, label)
                     count += 1

            # 2. Mask Coords -> Pixel Mask (Fallback / specific key)
            elif "mask_coords" in det:
                 coords = det["mask_coords"]
                 if isinstance(coords, list) and len(coords) > 2:
                     item = self._manager.add_mask(coords, label=label, color=self._manager.default_color)
                     self._canvas.add_annotation_item(item)
                     count += 1

            # 3. BBox
            if "box" in det:
                if isinstance(det["box"], list) and len(det["box"]) == 4:
                    x1, y1, x2, y2 = det["box"]
                    w = x2 - x1
                    h = y2 - y1
                    item = self._manager.add_rect(x1, y1, w, h, label=label, color=self._manager.default_color)
                    self._canvas.add_annotation_item(item)
                    count += 1

        self._ignore_changes = False
        
        if count == 0 and len(detections) > 0:
            # Debugging helper: Parsing matched nothing, but we got data.
            keys = list(detections[0].keys())
            msg = f"Received {len(detections)} detections but added 0.\nFirst item keys: {keys}\nExpected: 'box' or 'coordinates'"
            self._status.showMessage(f"AutoSeg: Added 0 annotations. (Keys mismatch?)")
            QMessageBox.warning(self, "AutoSeg Debug", msg)
        elif count == 0:
             self._status.showMessage("AutoSeg: No objects detected (0 returned).")
        else:
            self._status.showMessage(f"AutoSeg: Added {count} annotations.")
        
    def _on_autoseg_yolo_error(self, message: str) -> None:
        self._status.showMessage(f"AutoSeg Error: {message}")
        QMessageBox.warning(self, "AutoSeg Error", message)
        
    def _on_autoseg_yolo_cancelled(self) -> None:
        if self._autoseg_worker and self._autoseg_worker.isRunning():
            self._autoseg_worker.cancel()
            self._autoseg_worker.wait(2000)
        self._status.showMessage("AutoSeg cancelled.")
        
    def _on_autoseg_yolo_finished(self) -> None:
        if self._autoseg_progress:
            try:
                self._autoseg_progress.canceled.disconnect(self._on_autoseg_yolo_cancelled)
            except (TypeError, RuntimeError):
                pass
            self._autoseg_progress.close()
            self._autoseg_progress = None
        self._autoseg_worker = None

