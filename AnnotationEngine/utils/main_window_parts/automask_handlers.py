from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

from core.automask_worker import AutoMaskWorker


def _read_automask_settings(window) -> tuple[str, int, str, list[str]]:
    settings = QSettings("PyVisionAnnotator", "PyVisionAnnotator")
    exe = str(settings.value("autoseg/model_path", ""))
    timeout = int(settings.value("autoseg/timeout", 120))

    device = str(settings.value("autoseg/device", "")).strip().lower()
    if not device:
        use_gpu_raw = settings.value("autoseg/use_gpu", False)
        if isinstance(use_gpu_raw, str):
            use_gpu = use_gpu_raw.strip().lower() in {"1", "true", "yes", "on"}
        else:
            use_gpu = bool(use_gpu_raw)
        device = "cuda" if use_gpu else "cpu"

    extra_args = window._parse_custom_args(settings.value("autoseg/extra_args", ""))
    return exe, timeout, device, extra_args


def _start_automask_worker(
    window,
    image_path: str,
    point_x: int,
    point_y: int,
    all_segments: bool,
    executable: str,
    timeout: int,
    device: str,
    extra_args: list[str],
) -> None:
    window._automask_worker = AutoMaskWorker(
        executable=executable,
        script=None,
        image_path=image_path,
        point_x=point_x,
        point_y=point_y,
        device=device,
        extra_args=extra_args,
        timeout=timeout,
        all_segments=all_segments,
        parent=window,
    )
    window._automask_worker.result_ready.connect(window._on_autoseg_result)
    window._automask_worker.error_occurred.connect(window._on_autoseg_error)
    window._automask_worker.finished.connect(window._on_autoseg_worker_finished)
    window._automask_worker.start()


def on_autoseg_requested(window, scene_pos) -> None:
    """Canvas emitted an AutoSeg click - launch the segmentation subprocess."""
    exe, timeout, device, extra_args = _read_automask_settings(window)

    if not exe:
        window._canvas.autoseg_error_received("AutoSeg not configured.")
        window._status.showMessage("AutoMask not configured - open Settings first.")
        return

    image_path = window._manager.image_path
    if not image_path:
        window._canvas.autoseg_error_received("No image loaded.")
        return

    px = int(round(scene_pos.x()))
    py = int(round(scene_pos.y()))

    window._status.showMessage(f"AutoMask: segmenting at ({px}, {py}) - please wait ...")
    window._autoseg_progress = QProgressDialog("Running segmentation model ...", "Cancel", 0, 0, window)
    window._autoseg_progress.setWindowTitle("AutoMask")
    window._autoseg_progress.setMinimumDuration(0)
    window._autoseg_progress.canceled.connect(window._on_autoseg_cancelled)
    window._autoseg_progress.show()

    _start_automask_worker(
        window,
        image_path=image_path,
        point_x=px,
        point_y=py,
        all_segments=False,
        executable=exe,
        timeout=timeout,
        device=device,
        extra_args=extra_args,
    )


def on_autoseg_result(window, data: dict | list) -> None:
    """AutoSegWorker succeeded - forward result to canvas."""
    if isinstance(data, list):
        count = 0
        window._ignore_changes = True
        for det in data:
            label = det.get("label", "Object")
            coords = det.get("coordinates", [])
            if coords and len(coords) > 2:
                color = window._manager.get_color_for_label(label)
                item = window._manager.add_mask(coords, label=label, color=color)
                window._canvas.add_annotation_item(item)
                count += 1
        window._ignore_changes = False

        window._status.showMessage(f"AutoMask (--all): Added {count} masks.")
        window._canvas.autoseg_result_received({})
        return

    label = data.get("label", "")
    n_pts = len(data.get("coordinates", []))
    window._status.showMessage(
        f"AutoMask: segmented \"{label}\" - {n_pts} boundary points -> mask created."
    )
    window._canvas.autoseg_result_received(data)


def on_automask_all_requested(window) -> None:
    """Run AutoMask with --all (Segment Everything)."""
    exe, timeout, device, extra_args = _read_automask_settings(window)

    if not exe:
        window._status.showMessage("AutoMask not configured - open Settings first.")
        QMessageBox.warning(window, "AutoMask Not Configured", "Please configure the AutoMask model path first.")
        return

    image_path = window._manager.image_path
    if not image_path:
        window._status.showMessage("No image loaded.")
        return

    window._status.showMessage("AutoMask: segmenting everything - please wait ...")
    window._autoseg_progress = QProgressDialog(
        "Running AutoMask (Segment Everything) ...", "Cancel", 0, 0, window
    )
    window._autoseg_progress.setWindowTitle("AutoMask --all")
    window._autoseg_progress.setMinimumDuration(0)
    window._autoseg_progress.canceled.connect(window._on_autoseg_cancelled)
    window._autoseg_progress.show()

    _start_automask_worker(
        window,
        image_path=image_path,
        point_x=0,
        point_y=0,
        all_segments=True,
        executable=exe,
        timeout=timeout,
        device=device,
        extra_args=extra_args,
    )


def on_autoseg_error(window, message: str) -> None:
    """AutoSegWorker failed."""
    window._canvas.autoseg_error_received(message)
    window._status.showMessage("AutoMask: segmentation failed.")
    QMessageBox.warning(window, "AutoMask Error", message)


def on_autoseg_cancelled(window) -> None:
    """User pressed Cancel on the progress dialog."""
    if window._automask_worker and window._automask_worker.isRunning():
        window._automask_worker.cancel()
        window._automask_worker.wait(3000)
    window._canvas._autoseg_reset()
    window._status.showMessage("AutoMask: cancelled.")


def on_autoseg_worker_finished(window) -> None:
    """Clean up progress dialog when the worker thread finishes."""
    if window._autoseg_progress:
        window._autoseg_progress.close()
        window._autoseg_progress = None
    window._automask_worker = None


