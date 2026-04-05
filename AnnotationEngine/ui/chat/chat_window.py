"""Standalone chat window launched from the main toolbar."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox, QWidget

from core.chat.chat_protocol import HTTP_BASE_DEFAULT
from core.workers.chat_stomp_worker import ChatStompWorker
from core.chat.collab_protocol import COLLAB_WS_PATH, COLLAB_WS_URL_DEFAULT
from core.chat.collab_rest import CollabRestClient
from core.chat.collab_stomp_worker import CollabStompWorker
from ui.chat.chat_window_settings import (
    base_origin,
    build_ws_url,
    extract_token,
    extract_user_id,
    get_selected_profile,
    load_chat_ws_default,
    load_collab_ws_default,
    load_saved_session,
    load_server_base_default,
    persist_server_settings,
    populate_profiles,
)
from ui.chat.chat_window_connection import (
    close_event,
    on_chat_connected,
    on_chat_disconnected,
    on_chat_error,
    on_connect_requested,
    on_disconnect_requested,
    on_functional_error,
    on_worker_finished,
)
from ui.chat.chat_window_collab import (
    collab_client,
    download_image_from_event,
    on_collab_create_session,
    on_collab_event_received,
    on_collab_join_session,
    on_collab_refresh_sessions,
    on_collab_upload_image,
    send_collab_event,
    start_collab_worker,
    upload_current_image,
)
from ui.chat.chat_window_messages import (
    append_system,
    format_timestamp,
    get_receiver,
    on_clear_messages,
    on_history,
    on_history_received,
    on_presence,
    on_presence_item_clicked,
    on_presence_snapshot,
    on_presence_update,
    on_private_message,
    on_send,
)
from ui.chat.chat_window_ui import bind_chat_signals, build_chat_ui, open_advanced_popup

_ORG = "PyVisionAnnotator"
_APP = "PyVisionAnnotator"


class ChatWindow(QWidget):
    collab_event_received = pyqtSignal(dict)
    collab_snapshot_received = pyqtSignal(dict)

    def __init__(self, parent=None, current_image_path_fn=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Realtime Chat")
        self.resize(780, 560)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._stomp_worker: ChatStompWorker | None = None
        self._collab_worker: CollabStompWorker | None = None
        self._jwt: str = ""
        self._user_id: str = ""
        self._collab_session: dict[str, Any] = {}
        self._collab_version: int = 0
        self._current_image_path_fn = current_image_path_fn
        self._collab_ws_url: str = COLLAB_WS_URL_DEFAULT

        self._build_ui()
        self._bind_signals()
        # Populate available saved profiles and load the currently selected one
        self._populate_profiles()
        self._load_saved_session(show_message=False, session_name=self._get_selected_profile())

    def _build_ui(self) -> None:
        build_chat_ui(self)

    def _apply_style(self) -> None:
        # Intentionally keep native/default Qt style for this window.
        self.setStyleSheet("")

    def _set_connected_state(self, connected: bool) -> None:
        self.btn_connect.setEnabled(not connected)
        self.btn_disconnect.setEnabled(connected)
        self.btn_send.setEnabled(connected)
        self.btn_load_history.setEnabled(connected)
        self.btn_refresh_presence.setEnabled(connected)
        self.btn_clear_messages.setEnabled(True)
        self.btn_collab_refresh.setEnabled(connected)
        self.btn_collab_create.setEnabled(connected)
        self.btn_collab_join.setEnabled(connected)

    def _bind_signals(self) -> None:
        bind_chat_signals(self)

    def _on_profile_switched(self, _: int) -> None:
        self._load_saved_session(show_message=False, session_name=self._get_selected_profile())
        profile = self.combo_profiles.currentText().strip() or "default"
        QMessageBox.information(self, "Chat", f"Profile switched to: {profile}")

    def _open_advanced_popup(self) -> None:
        open_advanced_popup(self)

    def _load_saved_session(self, show_message: bool, session_name: str | None = None) -> None:
        load_saved_session(self, show_message=show_message, session_name=session_name)

    def _populate_profiles(self) -> None:
        populate_profiles(self)

    def _get_selected_profile(self) -> str | None:
        return get_selected_profile(self)

    @staticmethod
    def _extract_token(payload: dict[str, Any]) -> str:
        return extract_token(payload)

    @staticmethod
    def _extract_user_id(payload: dict[str, Any]) -> str:
        return extract_user_id(payload)

    @staticmethod
    def _build_ws_url(base_url: str, path: str) -> str:
        return build_ws_url(base_url, path)

    @staticmethod
    def _base_origin(url_value: str) -> str:
        return base_origin(url_value)

    def _load_server_base_default(self) -> str:
        return load_server_base_default()

    def _load_chat_ws_default(self, base_default: str) -> str:
        return load_chat_ws_default(base_default)

    def _load_collab_ws_default(self, base_default: str) -> str:
        return load_collab_ws_default(base_default)

    def _persist_server_settings(self) -> None:
        base_url = self.edit_base_url.text().strip() or HTTP_BASE_DEFAULT
        chat_ws = self.edit_ws_url.text().strip() or self._build_ws_url(base_url, "/ws")
        collab_ws = self._build_ws_url(base_url, COLLAB_WS_PATH)
        self._collab_ws_url = collab_ws
        persist_server_settings(base_url=base_url, chat_ws=chat_ws, collab_ws=collab_ws)

    def _on_connect_requested(self) -> None:
        on_connect_requested(self)

    def _on_disconnect_requested(self) -> None:
        on_disconnect_requested(self)

    def _on_chat_connected(self) -> None:
        on_chat_connected(self)

    def _on_chat_disconnected(self, reason: str) -> None:
        on_chat_disconnected(self, reason)

    def _on_chat_error(self, message: str) -> None:
        on_chat_error(self, message)

    def _on_functional_error(self, message: str) -> None:
        on_functional_error(self, message)

    def _on_worker_finished(self) -> None:
        on_worker_finished(self)

    def _start_collab_worker(self) -> None:
        start_collab_worker(self)

    def _collab_client(self) -> CollabRestClient:
        return collab_client(self)

    def _on_collab_refresh_sessions(self) -> None:
        on_collab_refresh_sessions(self)

    def _on_collab_create_session(self) -> None:
        on_collab_create_session(self)

    def _on_collab_join_session(self) -> None:
        on_collab_join_session(self)

    def _on_collab_upload_image(self) -> None:
        on_collab_upload_image(self)

    def send_collab_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        return send_collab_event(self, event_type, payload)

    def download_collab_image(self, envelope: dict) -> tuple[bool, str, str]:
        return download_image_from_event(self, envelope)

    def upload_current_collab_image(self, show_message: bool = False) -> bool:
        return upload_current_image(self, show_message=show_message)

    def _on_collab_event_received(self, payload: dict) -> None:
        on_collab_event_received(self, payload)

    def _get_receiver(self) -> str:
        return get_receiver(self)

    def _on_send(self) -> None:
        on_send(self)

    def _on_history(self) -> None:
        on_history(self)

    def _on_presence(self) -> None:
        on_presence(self)

    def _on_clear_messages(self) -> None:
        on_clear_messages(self)

    def _on_private_message(self, payload: dict) -> None:
        on_private_message(self, payload)

    def _on_history_received(self, messages: list) -> None:
        on_history_received(self, messages)

    def _on_presence_snapshot(self, users: list) -> None:
        on_presence_snapshot(self, users)

    def _on_presence_update(self, payload: dict) -> None:
        on_presence_update(self, payload)

    def _on_presence_item_clicked(self, item: QListWidgetItem) -> None:
        on_presence_item_clicked(self, item)

    def _append_system(self, text: str) -> None:
        append_system(self, text)

    @staticmethod
    def _format_timestamp(raw: Any) -> str:
        return format_timestamp(raw)

    def closeEvent(self, event) -> None:  # noqa: N802
        close_event(self, event)
