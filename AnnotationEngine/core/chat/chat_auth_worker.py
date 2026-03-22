"""Background HTTP auth worker for the separate chat window."""
from __future__ import annotations

import json
from urllib import error, request

from PyQt6.QtCore import QThread, pyqtSignal


class ChatAuthWorker(QThread):
    success = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(
        self,
        url: str,
        email: str,
        password: str,
        timeout: int = 15,
        success_statuses: tuple[int, ...] = (200,),
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._email = email
        self._password = password
        self._timeout = timeout
        self._success_statuses = success_statuses
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @staticmethod
    def _read_reason(raw: str) -> str:
        if not raw:
            return "Unknown error"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip() or "Unknown error"
        for key in ("reason", "message", "detail", "error"):
            val = body.get(key)
            if val:
                return str(val)
        return raw.strip() or "Unknown error"

    def run(self) -> None:
        payload = json.dumps({"email": self._email, "password": self._password}).encode("utf-8")
        req = request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout) as response:
                status = getattr(response, "status", response.getcode())
                raw = response.read().decode("utf-8", errors="replace")
                if self._cancelled:
                    return
                if status not in self._success_statuses:
                    self.failed.emit(f"Request failed ({status}): {self._read_reason(raw)}")
                    return
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    self.failed.emit("Server returned invalid JSON.")
                    return
                self.success.emit(data)
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            if not self._cancelled:
                self.failed.emit(f"Request failed ({exc.code}): {self._read_reason(raw) or exc.reason}")
        except error.URLError as exc:
            if not self._cancelled:
                self.failed.emit(f"Network error: {exc.reason}")
        except Exception as exc:  # pragma: no cover
            if not self._cancelled:
                self.failed.emit(f"Unexpected error: {exc}")

