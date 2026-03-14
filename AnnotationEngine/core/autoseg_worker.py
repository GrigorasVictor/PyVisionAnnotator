"""
core/autoseg_worker.py — Background worker for YOLO-based AutoSeg subprocess calls.

Runs the external YOLO segmentation model in a QThread.
Emits ``result_ready(list)`` on success or ``error_occurred(str)`` on failure.
"""
from __future__ import annotations

import json
from typing import Optional, List

from PyQt6.QtCore import QThread, pyqtSignal

from core.subprocess_handler import SubprocessHandler, ManagedProcess


class AutoSegWorker(QThread):
    """Execute an external YOLO segmentation model in a background thread.

    Signals:
        result_ready(list)  — parsed JSON list of detections from the subprocess.
        error_occurred(str) — human-readable error message.
    """

    result_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        executable: str,        # executable path
        script: Optional[str],  # optional script path (e.g. for python)
        image_path: str,
        labels: str,            # comma-separated labels
        conf_threshold: float = 0.32,
        device: str = "cuda",
        timeout: int = 300,
        mode: List[str] = None, # new parameter
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._executable = executable
        self._script = script
        self._image_path = image_path
        self._labels = labels
        self._conf = conf_threshold
        self._device = device
        self._timeout = timeout
        self._mode = mode if mode else ["bbox", "segment"]
        self._managed: Optional[ManagedProcess] = None

    def cancel(self) -> None:
        if self._managed is not None:
            self._managed.kill()

    def run(self) -> None:
        args = [
            "--image", self._image_path,
            "--labels", self._labels,
            "--conf", str(self._conf),
            "--device", self._device,
            "--mode", *self._mode
        ]

        self._managed, err = SubprocessHandler.start_process(
            executable=self._executable,
            script=self._script,
            args=args,
            timeout=self._timeout,
        )

        if self._managed is None:
            self.error_occurred.emit(f"AutoSeg subprocess failed to start:\n{err}")
            return

        success, data, error = self._managed.wait()

        if self._managed.killed:
            return

        if not success:
            self.error_occurred.emit(f"AutoSeg subprocess failed:\n{error}")
            return

        if not isinstance(data, list):
             # Maybe it returned a single dict? User's snippet showed one detection dict.
             # If the script outputs just one JSON object representing a list, fine.
             # If it outputs multiple JSON logic lines, SubprocessHandler might need adjustment.
             # Assuming SubprocessHandler.parse_json_output handles standard JSON.
             if isinstance(data, dict):
                 data = [data]
             else:
                self.error_occurred.emit(
                    f"AutoSeg subprocess returned unexpected output format:\n{type(data)}"
                )
                return

        self.result_ready.emit(data)

