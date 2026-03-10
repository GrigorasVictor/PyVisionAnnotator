"""
core/autoseg_worker.py — Background worker for AutoSeg subprocess calls.

Runs the external segmentation model in a QThread so the GUI stays responsive.
Emits ``result_ready(dict)`` on success or ``error_occurred(str)`` on failure.
The underlying OS process can be force-killed via ``cancel()`` from any thread.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core.subprocess_handler import SubprocessHandler, ManagedProcess


class AutoSegWorker(QThread):
    """Execute an external segmentation model in a background thread.

    Signals:
        result_ready(dict)  — parsed JSON response from the subprocess.
        error_occurred(str) — human-readable error message.
    """

    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        executable: str,
        script: Optional[str],
        image_path: str,
        point_x: int,
        point_y: int,
        timeout: int = 120,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._executable = executable
        self._script = script
        self._image_path = image_path
        self._point_x = point_x
        self._point_y = point_y
        self._timeout = timeout
        self._managed: Optional[ManagedProcess] = None

    # ---- public: safe cancel ----------------------------------------- #
    def cancel(self) -> None:
        """Kill the running subprocess immediately (safe from any thread).

        The thread will exit naturally once ``ManagedProcess.wait()``
        returns with the "cancelled" status — no need for QThread.terminate().
        """
        if self._managed is not None:
            self._managed.kill()

    # ---- thread entry point ------------------------------------------ #
    def run(self) -> None:
        """Called automatically by QThread.start() — runs in the worker thread."""
        point_str = f"{self._point_x},{self._point_y}"

        self._managed, err = SubprocessHandler.start_process(
            executable=self._executable,
            script=self._script,
            args=["--image", self._image_path, "--point", point_str, "--device", "cuda"],
            timeout=self._timeout,
        )

        if self._managed is None:
            self.error_occurred.emit(f"AutoSeg subprocess failed to start:\n{err}")
            return

        success, data, error = self._managed.wait()

        # If the user cancelled, exit silently (no error popup)
        if self._managed.killed:
            return

        if not success:
            self.error_occurred.emit(f"AutoSeg subprocess failed:\n{error}")
            return

        if not isinstance(data, dict):
            self.error_occurred.emit(
                f"AutoSeg subprocess returned unexpected output:\n{data}"
            )
            return

        if "coordinates" not in data:
            self.error_occurred.emit(
                f"AutoSeg response missing 'coordinates' key.\nKeys: {list(data.keys())}"
            )
            return

        self.result_ready.emit(data)

