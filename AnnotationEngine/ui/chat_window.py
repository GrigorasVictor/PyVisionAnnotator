"""Standalone chat window launched from the main toolbar."""
from __future__ import annotations

from datetime import datetime
import importlib.util
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.chat.chat_protocol import WS_URL_DEFAULT
from core.chat.chat_stomp_worker import ChatStompWorker
from utils.auth_store import load_auth_payload, list_saved_sessions


class ChatWindow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Realtime Chat")
        self.resize(780, 560)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._stomp_worker: ChatStompWorker | None = None
        self._jwt: str = ""
        self._user_id: str = ""

        self._build_ui()
        self._bind_signals()
        # Populate available saved profiles and load the currently selected one
        self._populate_profiles()
        self._load_saved_session(show_message=False, session_name=self._get_selected_profile())

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        config_box = QGroupBox("Connection")
        config_layout = QGridLayout(config_box)

        self.edit_ws_url = QLineEdit(WS_URL_DEFAULT)
        self.lbl_session = QLabel("No saved session")
        # Profile selection: choose which saved session to load
        self.combo_profiles = QComboBox()
        self.btn_refresh_profiles = QPushButton("Refresh Profiles")
        self.chk_show_raw_presence = QCheckBox("Show raw presence")

        self.btn_reload_session = QPushButton("Reload Session")
        self.btn_connect = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")

        config_layout.addWidget(QLabel("WebSocket URL:"), 0, 0)
        config_layout.addWidget(self.edit_ws_url, 0, 1, 1, 3)
        config_layout.addWidget(QLabel("Session:"), 1, 0)
        config_layout.addWidget(self.lbl_session, 1, 1, 1, 3)
        config_layout.addWidget(QLabel("Profile:"), 3, 0)
        config_layout.addWidget(self.combo_profiles, 3, 1, 1, 1)
        config_layout.addWidget(self.btn_refresh_profiles, 3, 2)
        config_layout.addWidget(self.chk_show_raw_presence, 3, 3)
        config_layout.addWidget(self.btn_reload_session, 2, 0)
        config_layout.addWidget(self.btn_connect, 2, 2)
        config_layout.addWidget(self.btn_disconnect, 2, 3)

        root.addWidget(config_box)

        split = QHBoxLayout()

        left_box = QGroupBox("Online Users")
        left_layout = QVBoxLayout(left_box)
        self.list_presence = QListWidget()
        self.btn_refresh_presence = QPushButton("Refresh Presence")
        left_layout.addWidget(self.list_presence)
        left_layout.addWidget(self.btn_refresh_presence)

        right_box = QGroupBox("Conversation")
        right_layout = QVBoxLayout(right_box)

        receiver_row = QHBoxLayout()
        receiver_row.addWidget(QLabel("Receiver:"))
        self.edit_receiver = QLineEdit()
        receiver_row.addWidget(self.edit_receiver)
        self.btn_load_history = QPushButton("Load History")
        receiver_row.addWidget(self.btn_load_history)

        self.text_messages = QTextEdit()
        self.text_messages.setReadOnly(True)

        send_row = QHBoxLayout()
        self.edit_message = QLineEdit()
        self.edit_message.setPlaceholderText("Type a private message...")
        self.btn_send = QPushButton("Send")
        send_row.addWidget(self.edit_message)
        send_row.addWidget(self.btn_send)

        right_layout.addLayout(receiver_row)
        right_layout.addWidget(self.text_messages)
        right_layout.addLayout(send_row)

        split.addWidget(left_box, 1)
        split.addWidget(right_box, 3)

        root.addLayout(split)

        self.lbl_status = QLabel("Not connected")
        root.addWidget(self.lbl_status)

    def _bind_signals(self) -> None:
        self.btn_reload_session.clicked.connect(lambda: self._load_saved_session(show_message=True, session_name=self._get_selected_profile()))
        self.btn_connect.clicked.connect(self._on_connect_requested)
        self.btn_disconnect.clicked.connect(self._on_disconnect_requested)
        self.btn_send.clicked.connect(self._on_send)
        self.btn_load_history.clicked.connect(self._on_history)
        self.btn_refresh_presence.clicked.connect(self._on_presence)
        self.list_presence.itemClicked.connect(self._on_presence_item_clicked)
        self.btn_refresh_profiles.clicked.connect(self._populate_profiles)
        self.combo_profiles.activated.connect(lambda _: self._load_saved_session(show_message=False, session_name=self._get_selected_profile()))
        self.chk_show_raw_presence.stateChanged.connect(lambda _: None)

    def _load_saved_session(self, show_message: bool, session_name: str | None = None) -> None:
        payload = load_auth_payload(session_name) or {}
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        self._jwt = self._extract_token(data)
        self._user_id = self._extract_user_id(data)

        if self._jwt:
            who = self._user_id or "authenticated user"
            self.lbl_session.setText(f"Loaded JWT for {who}")
            if show_message:
                QMessageBox.information(self, "Chat", "Session loaded from saved auth payload.")
        else:
            self.lbl_session.setText("No token found. Use Account login first.")
            if show_message:
                QMessageBox.warning(self, "Chat", "No JWT found in saved session.")

    def _populate_profiles(self) -> None:
        """Populate the profiles combo with saved session files."""
        self.combo_profiles.clear()
        for p in list_saved_sessions():
            # show filename, store stem (without .json) as session_name
            try:
                name = p.name
                stem = p.stem
            except Exception:
                continue
            # Skip the default session.json entry since we already added a default
            if name == "session.json":
                continue
            self.combo_profiles.addItem(name, stem)

    def _get_selected_profile(self) -> str | None:
        data = self.combo_profiles.currentData()
        return data if data is not None else None

    @staticmethod
    def _extract_token(payload: dict[str, Any]) -> str:
        for key in ("token", "accessToken", "jwt", "access_token"):
            value = payload.get(key)
            if value:
                return str(value)
        nested = payload.get("data")
        if isinstance(nested, dict):
            for key in ("token", "accessToken", "jwt", "access_token"):
                value = nested.get(key)
                if value:
                    return str(value)
        return ""

    @staticmethod
    def _extract_user_id(payload: dict[str, Any]) -> str:
        for key in ("email", "userId", "username", "sub"):
            value = payload.get(key)
            if value:
                return str(value)
        user = payload.get("user")
        if isinstance(user, dict):
            for key in ("email", "userId", "username"):
                value = user.get(key)
                if value:
                    return str(value)
        return ""

    def _on_connect_requested(self) -> None:
        if importlib.util.find_spec("websocket") is None:
            QMessageBox.warning(self, "Chat", "Packet 'websocket-client' missing. Run: pip install websocket-client")
            return
        # Ensure we load the profile currently selected in the UI
        self._load_saved_session(show_message=False, session_name=self._get_selected_profile())
        if not self._jwt:
            QMessageBox.warning(self, "Chat", "No auth session detected. Go login first.")
            return
        if self._stomp_worker and self._stomp_worker.isRunning():
            self.lbl_status.setText("Chat already connected.")
            return

        ws_url = self.edit_ws_url.text().strip() or WS_URL_DEFAULT
        self._stomp_worker = ChatStompWorker(ws_url=ws_url, jwt_token=self._jwt, parent=self)
        self._stomp_worker.connected.connect(self._on_chat_connected)
        self._stomp_worker.disconnected.connect(self._on_chat_disconnected)
        self._stomp_worker.connection_error.connect(self._on_chat_error)
        self._stomp_worker.private_message.connect(self._on_private_message)
        self._stomp_worker.history_received.connect(self._on_history_received)
        self._stomp_worker.presence_snapshot.connect(self._on_presence_snapshot)
        self._stomp_worker.presence_update.connect(self._on_presence_update)
        self._stomp_worker.functional_error.connect(self._on_functional_error)
        self._stomp_worker.finished.connect(self._on_worker_finished)
        self._stomp_worker.start()
        self.lbl_status.setText("Connecting to websocket...")

    def _on_disconnect_requested(self) -> None:
        if self._stomp_worker:
            self._stomp_worker.stop(manual=True)

    def _on_chat_connected(self) -> None:
        self.lbl_status.setText("Connected")
        self._append_system("WebSocket/STOMP connected.")
        if self._stomp_worker:
            self._stomp_worker.request_presence()

    def _on_chat_disconnected(self, reason: str) -> None:
        self.lbl_status.setText(reason)
        self._append_system(reason)

    def _on_chat_error(self, message: str) -> None:
        self.lbl_status.setText("Connection error")
        self._append_system(f"Connection error: {message}")

    def _on_functional_error(self, message: str) -> None:
        self._append_system(f"Server error: {message}")

    def _on_worker_finished(self) -> None:
        self._stomp_worker = None

    def _on_send(self) -> None:
        if not self._stomp_worker:
            QMessageBox.warning(self, "Chat", "Not connected.")
            return
        receiver = self.edit_receiver.text().strip()
        text = self.edit_message.text().strip()
        if not receiver or not text:
            return
        self._stomp_worker.send_private(receiver, text)
        self.edit_message.clear()

    def _on_history(self) -> None:
        if not self._stomp_worker:
            QMessageBox.warning(self, "Chat", "Not connected.")
            return
        receiver = self.edit_receiver.text().strip()
        if not receiver:
            return
        self._stomp_worker.request_history(receiver)

    def _on_presence(self) -> None:
        if self._stomp_worker:
            self._stomp_worker.request_presence()

    def _on_private_message(self, payload: dict) -> None:
        sender = str(payload.get("senderId") or payload.get("senderDisplayName") or "unknown")
        message = str(payload.get("message") or "")
        ts = self._format_timestamp(payload.get("timestamp"))
        self.text_messages.append(f"[{ts}] {sender}: {message}")

    def _on_history_received(self, messages: list) -> None:
        self.text_messages.clear()
        for item in messages:
            if isinstance(item, dict):
                self._on_private_message(item)

    def _on_presence_snapshot(self, users: list) -> None:
        self.list_presence.clear()
        if isinstance(users, list) and len(users) == 1 and isinstance(users[0], dict) and "onlineUsers" in users[0]:
            entries = users[0]["onlineUsers"]
        elif isinstance(users, dict) and "onlineUsers" in users:
            entries = users["onlineUsers"]
        else:
            entries = users if isinstance(users, list) else [users]

        my = (self._user_id or "").strip().lower()
        for e in entries:
            if isinstance(e, dict):
                disp = str(e.get("userId") or e.get("email") or e.get("username") or e.get("id") or e)
                ident = (str(e.get("userId") or e.get("email") or e.get("username") or e.get("id") or e)).strip().lower()
            else:
                disp = str(e)
                ident = str(e).strip().lower()
            if my and ident == my:
                disp = f"{disp} (you)"
            self.list_presence.addItem(QListWidgetItem(disp))

    def _on_presence_update(self, payload: dict) -> None:
        user = str(payload.get("userId") or payload.get("email") or "unknown")
        status = str(payload.get("status") or payload.get("event") or "update")
        self._append_system(f"Presence: {user} -> {status}")

    def _on_presence_item_clicked(self, item: QListWidgetItem) -> None:
        self.edit_receiver.setText(item.text().strip())

    def _append_system(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.text_messages.append(f"[{ts}] [system] {text}")

    @staticmethod
    def _format_timestamp(raw: Any) -> str:
        # Prefer using the provided timestamp if possible. Expect ISO-like strings
        # such as 2026-03-22T15:02:44.631497347 or with trailing Z.
        from datetime import datetime as _dt
        if not raw:
            return _dt.now().strftime("%H:%M:%S")
        try:
            s = str(raw).strip()
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'
            # Trim fractional seconds to microseconds (6 digits) for fromisoformat
            if '.' in s:
                head, tail = s.split('.', 1)
                frac = tail
                # keep timezone suffix if present
                tz = ''
                for sign in ('+', '-'):
                    if sign in tail:
                        frac, tz = tail.split(sign, 1)
                        tz = sign + tz
                        break
                frac = (frac + '000000')[:6]
                s = head + '.' + frac + tz
            dt = _dt.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt
            return dt.strftime("%H:%M:%S")
        except Exception:
            return _dt.now().strftime("%H:%M:%S")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._stomp_worker:
            self._stomp_worker.stop(manual=True)
        super().closeEvent(event)

