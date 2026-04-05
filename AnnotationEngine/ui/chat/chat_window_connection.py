"""Connection lifecycle handlers for ChatWindow."""
from __future__ import annotations

import importlib.util

from PyQt6.QtWidgets import QMessageBox, QWidget

from core.chat.chat_protocol import WS_URL_DEFAULT
from core.workers.chat_stomp_worker import ChatStompWorker


def on_connect_requested(window) -> None:
    if importlib.util.find_spec("websocket") is None:
        QMessageBox.warning(window, "Chat", "Packet 'websocket-client' missing. Run: pip install websocket-client")
        return
    window._persist_server_settings()
    window._load_saved_session(show_message=False, session_name=window._get_selected_profile())
    if not window._jwt:
        QMessageBox.warning(window, "Chat", "No auth session detected. Go login first.")
        return
    if window._stomp_worker and window._stomp_worker.isRunning():
        window.lbl_status.setText("Chat already connected.")
        return

    ws_url = window.edit_ws_url.text().strip() or WS_URL_DEFAULT
    QMessageBox.information(window, "Chat", "Connecting to chat server...")
    window._stomp_worker = ChatStompWorker(ws_url=ws_url, jwt_token=window._jwt, parent=window)
    window._stomp_worker.connected.connect(window._on_chat_connected)
    window._stomp_worker.disconnected.connect(window._on_chat_disconnected)
    window._stomp_worker.connection_error.connect(window._on_chat_error)
    window._stomp_worker.private_message.connect(window._on_private_message)
    window._stomp_worker.history_received.connect(window._on_history_received)
    window._stomp_worker.presence_snapshot.connect(window._on_presence_snapshot)
    window._stomp_worker.presence_update.connect(window._on_presence_update)
    window._stomp_worker.functional_error.connect(window._on_functional_error)
    window._stomp_worker.finished.connect(window._on_worker_finished)
    window._stomp_worker.start()
    window.lbl_status.setText("Connecting to websocket...")
    window._start_collab_worker()


def on_disconnect_requested(window) -> None:
    if window._stomp_worker:
        QMessageBox.information(window, "Chat", "Disconnect requested.")
        window._stomp_worker.stop(manual=True)
    if window._collab_worker:
        window._collab_worker.stop(manual=True)


def on_chat_connected(window) -> None:
    window.lbl_status.setText("Connected")
    window._set_connected_state(True)
    window._append_system("WebSocket/STOMP connected.")
    QMessageBox.information(window, "Chat", "Connected successfully.")
    if window._stomp_worker:
        window._stomp_worker.request_presence()


def on_chat_disconnected(window, reason: str) -> None:
    window.lbl_status.setText(reason)
    window._set_connected_state(False)
    window._append_system(reason)


def on_chat_error(window, message: str) -> None:
    window.lbl_status.setText("Connection error")
    window._set_connected_state(False)
    window._append_system(f"Connection error: {message}")


def on_functional_error(window, message: str) -> None:
    window._append_system(f"Server error: {message}")


def on_worker_finished(window) -> None:
    window._stomp_worker = None
    window._set_connected_state(False)


def close_event(window, event) -> None:
    if window._stomp_worker:
        window._stomp_worker.stop(manual=True)
    if window._collab_worker:
        window._collab_worker.stop(manual=True)
    QWidget.closeEvent(window, event)


