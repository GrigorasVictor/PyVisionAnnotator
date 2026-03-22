"""Background worker for authentication HTTP requests."""
from __future__ import annotations

import json
from urllib import error, request

from PyQt6.QtCore import QThread, pyqtSignal


class AuthWorker(QThread):
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
    def _read_reason_from_body(raw: str) -> str:
        if not raw:
            return "Unknown error"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip() or "Unknown error"

        for key in ("reason", "message", "detail", "error"):
            value = data.get(key)
            if value:
                return str(value)
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
                status_code = getattr(response, "status", response.getcode())
                raw = response.read().decode("utf-8", errors="replace")
                if self._cancelled:
                    return
                if status_code not in self._success_statuses:
                    reason = self._read_reason_from_body(raw)
                    self.failed.emit(f"Authentication failed ({status_code}): {reason}")
                    return
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    self.failed.emit("Authentication failed: invalid JSON body returned by server.")
                    return
                self.success.emit(body)
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            reason = self._read_reason_from_body(raw) or str(exc.reason)
            if not self._cancelled:
                self.failed.emit(f"Authentication failed ({exc.code}): {reason}")
        except error.URLError as exc:
            if not self._cancelled:
                self.failed.emit(f"Authentication request error: {exc.reason}")
        except Exception as exc:  # pragma: no cover - unexpected runtime failures
            if not self._cancelled:
                self.failed.emit(f"Authentication failed: {exc}")

