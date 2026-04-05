"""YOLO full-image segmentation handlers for MainWindow.

Shows run dialog (labels+mode), spawns AutoSegYoloWorker, parses bbox/polygon/mask detections,
adds items to manager + canvas, handles errors/cancellation + cleanup. Key: on_autoseg_yolo_run,
on_autoseg_yolo_result (add rects/polys/masks), on_autoseg_yolo_error/cancelled/finished.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QPointF, QSettings
from PyQt6.QtGui import QPolygonF
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

from core.workers.autoseg_worker import AutoSegWorker as AutoSegYoloWorker
from ui.main_window.autoseg_run_dialog import AutoSegRunDialog

logger = logging.getLogger(__name__)


def _add_polygon(window, coords: list, label: str) -> None:
    """Convert [[x, y], ...] into a vector PolygonItem."""
    poly = QPolygonF()
    for point in coords:
        if isinstance(point, list) and len(point) >= 2:
            poly.append(QPointF(float(point[0]), float(point[1])))

    if not poly.isEmpty():
        color = window._manager.get_color_for_label(label)
        item = window._manager.add_poly(poly, label=label, color=color)
        window._canvas.add_annotation_item(item)


def on_autoseg_yolo_run(window) -> None:
    """Run YOLO segmentation on the full image."""
    settings = QSettings("PyVisionAnnotator", "PyVisionAnnotator")

    executable = str(settings.value("autoseg_yolo/executable", ""))
    image_path = window._manager.image_path
    if not image_path:
        QMessageBox.warning(window, "No Image", "Please load an image first.")
        return

    # Optional weights path if the executable needs it.
    _ = settings.value("autoseg_yolo/model_path", "")
    conf = float(settings.value("autoseg_yolo/conf", 0.32))
    device = settings.value("autoseg_yolo/device", "cpu")
    extra_args = window._parse_custom_args(settings.value("autoseg_yolo/extra_args", ""))

    if not executable:
        QMessageBox.warning(window, "Not Configured", "Please set the YOLO Executable path in Settings.")
        return

    dlg = AutoSegRunDialog(window)
    if not dlg.exec():
        return

    labels, mode = dlg.get_values()
    if not labels:
        QMessageBox.warning(window, "No Labels", "Please enter at least one label.")
        return
    if not mode:
        QMessageBox.warning(window, "No Mode", "Please select at least one output mode (BBox or Segment).")
        return

    window._status.showMessage("Running AutoSeg (YOLO)...")
    window._autoseg_progress = QProgressDialog("Running YOLO segmentation...", "Cancel", 0, 0, window)
    window._autoseg_progress.setWindowTitle("AutoSeg (YOLO)")
    window._autoseg_progress.setMinimumDuration(0)
    window._autoseg_progress.canceled.connect(window._on_autoseg_yolo_cancelled)
    window._autoseg_progress.show()

    window._autoseg_worker = AutoSegYoloWorker(
        executable=executable,
        script=None,
        image_path=image_path,
        labels=labels,
        conf_threshold=conf,
        device=device,
        extra_args=extra_args,
        mode=mode,
        parent=window,
    )
    window._autoseg_worker.result_ready.connect(window._on_autoseg_yolo_result)
    window._autoseg_worker.error_occurred.connect(window._on_autoseg_yolo_error)
    window._autoseg_worker.finished.connect(window._on_autoseg_yolo_finished)
    window._autoseg_worker.start()


def on_autoseg_yolo_result(window, detections: list) -> None:
    """Process results from YOLO."""
    logger.info("AutoSeg received %s detections: %s", len(detections), detections)

    count = 0
    window._ignore_changes = True
    for det in detections:
        label = det.get("label", "Object")
        color = window._manager.get_color_for_label(label)

        if "coordinates" in det:
            coords = det["coordinates"]
            if isinstance(coords, list) and len(coords) > 2:
                _add_polygon(window, coords, label)
                count += 1
        elif "mask_coords" in det:
            coords = det["mask_coords"]
            if isinstance(coords, list) and len(coords) > 2:
                item = window._manager.add_mask(coords, label=label, color=color)
                window._canvas.add_annotation_item(item)
                count += 1

        if "box" in det and isinstance(det["box"], list) and len(det["box"]) == 4:
            x1, y1, x2, y2 = det["box"]
            item = window._manager.add_rect(x1, y1, x2 - x1, y2 - y1, label=label, color=color)
            window._canvas.add_annotation_item(item)
            count += 1

    window._ignore_changes = False

    if count == 0 and detections:
        keys = list(detections[0].keys())
        msg = (
            f"Received {len(detections)} detections but added 0.\n"
            f"First item keys: {keys}\n"
            "Expected: 'box' or 'coordinates'"
        )
        window._status.showMessage("AutoSeg: Added 0 annotations. (Keys mismatch?)")
        QMessageBox.warning(window, "AutoSeg Debug", msg)
    elif count == 0:
        window._status.showMessage("AutoSeg: No objects detected (0 returned).")
    else:
        window._status.showMessage(f"AutoSeg: Added {count} annotations.")


def on_autoseg_yolo_error(window, message: str) -> None:
    window._status.showMessage(f"AutoSeg Error: {message}")
    QMessageBox.warning(window, "AutoSeg Error", message)


def on_autoseg_yolo_cancelled(window) -> None:
    if window._autoseg_worker and window._autoseg_worker.isRunning():
        window._autoseg_worker.cancel()
        window._autoseg_worker.wait(2000)
    window._status.showMessage("AutoSeg cancelled.")


def on_autoseg_yolo_finished(window) -> None:
    if window._autoseg_progress:
        try:
            window._autoseg_progress.canceled.disconnect(window._on_autoseg_yolo_cancelled)
        except (TypeError, RuntimeError):
            pass
        window._autoseg_progress.close()
        window._autoseg_progress = None
    window._autoseg_worker = None

