from __future__ import annotations

from datetime import datetime, timezone

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

from core.auth_worker import AuthWorker
from ui.auth_login_dialog import AuthLoginDialog
from utils.auth_store import save_auth_payload

_DEFAULT_LOGIN_URL = "http://127.0.0.1:8080/auth/login"
_DEFAULT_REGISTER_URL = "http://127.0.0.1:8080/auth/register"


def _auth_endpoint(mode: str) -> str:
    settings = QSettings("PyVisionAnnotator", "PyVisionAnnotator")
    if mode == "register":
        value = settings.value("auth/register_url", _DEFAULT_REGISTER_URL)
        return str(value).strip() or _DEFAULT_REGISTER_URL
    value = settings.value("auth/login_url", _DEFAULT_LOGIN_URL)
    return str(value).strip() or _DEFAULT_LOGIN_URL


def on_auth_requested(window) -> None:
    dialog = AuthLoginDialog(window)
    if not dialog.exec():
        return

    mode, email, password, _confirm = dialog.get_submission()
    if not email or not password:
        QMessageBox.warning(window, "Authentication", "Email and password are required.")
        return

    if window._auth_worker and window._auth_worker.isRunning():
        QMessageBox.information(window, "Authentication", "An authentication request is already in progress.")
        return

    title = "Register" if mode == "register" else "Login"
    verb = "Creating account..." if mode == "register" else "Authenticating..."
    window._auth_progress = QProgressDialog(verb, "Cancel", 0, 0, window)
    window._auth_progress.setWindowTitle(f"Account - {title}")
    window._auth_progress.setMinimumDuration(0)
    window._auth_progress.canceled.connect(window._on_auth_cancelled)
    window._auth_progress.show()

    window._auth_mode = mode
    success_codes = (200, 201) if mode == "register" else (200,)
    window._auth_worker = AuthWorker(
        url=_auth_endpoint(mode),
        email=email,
        password=password,
        success_statuses=success_codes,
        parent=window,
    )
    window._auth_worker.success.connect(window._on_auth_success)
    window._auth_worker.failed.connect(window._on_auth_error)
    window._auth_worker.finished.connect(window._on_auth_finished)
    window._auth_worker.start()


def on_auth_success(window, payload: dict) -> None:
    mode = getattr(window, "_auth_mode", "login")
    wrapped_payload = {
        "mode": mode,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    path = save_auth_payload(wrapped_payload)
    msg = "Account created successfully." if mode == "register" else "Authenticated successfully."
    window._status.showMessage(msg)
    QMessageBox.information(window, "Account", f"{msg}\nSaved payload to:\n{path}")


def on_auth_error(window, message: str) -> None:
    mode = getattr(window, "_auth_mode", "login")
    op_name = "Registration" if mode == "register" else "Authentication"
    window._status.showMessage(f"{op_name} failed.")
    QMessageBox.warning(window, f"{op_name} Failed", message)


def on_auth_cancelled(window) -> None:
    if window._auth_worker and window._auth_worker.isRunning():
        window._auth_worker.cancel()
        window._status.showMessage("Authentication cancelled.")


def on_auth_finished(window) -> None:
    if window._auth_progress:
        try:
            window._auth_progress.canceled.disconnect(window._on_auth_cancelled)
        except (TypeError, RuntimeError):
            pass
        window._auth_progress.close()
        window._auth_progress = None
    window._auth_worker = None
    window._auth_mode = "login"

