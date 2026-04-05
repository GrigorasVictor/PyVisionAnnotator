"""Background worker for authentication HTTP requests.

POSTs email/password, emits success(dict) or failed(str). Retries localhost:8080 if localhost:80 refused.
Key: run (POST + JSON parse with fallback retry), cancel, _read_reason_from_body (extract error),
_fallback_url_for_localhost (connection refused recovery).
"""
from __future__ import annotations

import json
from urllib import error, parse, request

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

    @staticmethod
    def _fallback_url_for_localhost(url: str) -> str | None:
        try:
            u = parse.urlparse(url)
        except Exception:
            return None
        host = (u.hostname or "").lower()
        if host not in ("localhost", "127.0.0.1"):
            return None
        port = u.port
        if port not in (None, 80):
            return None
        scheme = u.scheme or "http"
        path = u.path or "/"
        query = f"?{u.query}" if u.query else ""
        return f"{scheme}://{host}:8080{path}{query}"

    def _perform_request(self, url: str) -> tuple[int, str]:
        payload = json.dumps({"email": self._email, "password": self._password}).encode("utf-8")
        req = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self._timeout) as response:
            status_code = getattr(response, "status", response.getcode())
            raw = response.read().decode("utf-8", errors="replace")
            return status_code, raw

    def run(self) -> None:
        # First try the configured URL; if localhost:80 is refused, retry localhost:8080 once.
        try_url = self._url
        tried_fallback = False
        while True:
            try:
                status_code, raw = self._perform_request(try_url)
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
                return
            except error.URLError as exc:
                reason = str(exc.reason)
                fallback = self._fallback_url_for_localhost(try_url)
                if (not tried_fallback) and fallback and ("refused" in reason.lower()):
                    tried_fallback = True
                    try_url = fallback
                    continue
                if not self._cancelled:
                    self.failed.emit(f"Authentication request error: {exc.reason}")
                return
            except error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                reason = self._read_reason_from_body(raw) or str(exc.reason)
                if not self._cancelled:
                    self.failed.emit(f"Authentication failed ({exc.code}): {reason}")
                return
            except Exception as exc:  # pragma: no cover - unexpected runtime failures
                if not self._cancelled:
                    self.failed.emit(f"Authentication failed: {exc}")
                return
