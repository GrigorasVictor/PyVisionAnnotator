"""Standalone chat window launched from the main toolbar."""
from __future__ import annotations

from datetime import datetime
import importlib.util
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self.edit_ws_url = QLineEdit(WS_URL_DEFAULT)
        self.edit_ws_url.setPlaceholderText("ws://host:port/ws")
        self.lbl_session = QLabel("No saved session")
        self.combo_profiles = QComboBox()
        self.btn_refresh_profiles = QPushButton("Refresh Profiles")
        self.chk_show_raw_presence = QCheckBox("Show raw presence")

        self.btn_reload_session = QPushButton("Reload Session")
        self.btn_connect = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_advanced = QPushButton("Advanced ")

        toolbar = QFrame(self)
        toolbar.setObjectName("chatToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(8)
        self.lbl_server = QLabel("Server:")
        self.lbl_identity = QLabel("Identity:")
        toolbar_layout.addWidget(self.lbl_server)
        toolbar_layout.addWidget(self.edit_ws_url, 2)
        toolbar_layout.addWidget(self.lbl_identity)
        toolbar_layout.addWidget(self.combo_profiles, 1)
        toolbar_layout.addWidget(self.btn_refresh_profiles)
        toolbar_layout.addWidget(self.btn_reload_session)
        toolbar_layout.addWidget(self.btn_connect)
        toolbar_layout.addWidget(self.btn_disconnect)
        toolbar_layout.addWidget(self.btn_advanced)
        root.addWidget(toolbar)

        info_row = QFrame(self)
        info_row.setObjectName("chatInfo")
        info_layout = QHBoxLayout(info_row)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(8)
        self.lbl_status = QLabel("Not connected")
        info_layout.addWidget(self.lbl_status)
        info_layout.addStretch(1)
        info_layout.addWidget(self.chk_show_raw_presence)
        info_layout.addWidget(self.lbl_session)
        root.addWidget(info_row)

        # Keep advanced controls out of the main chat surface.
        self.lbl_server.setVisible(False)
        self.lbl_identity.setVisible(False)
        self.edit_ws_url.setVisible(False)
        self.combo_profiles.setVisible(False)
        self.btn_refresh_profiles.setVisible(False)
        self.btn_reload_session.setVisible(False)
        self.chk_show_raw_presence.setVisible(False)
        self.lbl_session.setVisible(False)
        info_row.setVisible(False)

        split = QHBoxLayout()
        split.setSpacing(8)

        left_box = QGroupBox("Online Users")
        left_layout = QVBoxLayout(left_box)
        self.list_presence = QListWidget()
        self.btn_refresh_presence = QPushButton("Refresh Presence")
        left_layout.addWidget(self.list_presence)
        left_layout.addWidget(self.btn_refresh_presence)

        right_box = QGroupBox("Conversation")
        right_layout = QVBoxLayout(right_box)

        receiver_row = QHBoxLayout()
        receiver_row.addWidget(QLabel("Chat with:"))
        self.combo_receiver = QComboBox()
        self.combo_receiver.setEditable(True)
        self.combo_receiver.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_receiver.setPlaceholderText("Select user from left list")
        receiver_row.addWidget(self.combo_receiver)
        self.btn_load_history = QPushButton("Load History")
        receiver_row.addWidget(self.btn_load_history)

        self.text_messages = QTextEdit()
        self.text_messages.setReadOnly(True)

        send_row = QHBoxLayout()
        self.edit_message = QLineEdit()
        self.edit_message.setPlaceholderText("Type a private message...")
        self.btn_send = QPushButton("Send")
        self.btn_clear_messages = QPushButton("Clear Messages")
        send_row.addWidget(self.edit_message)
        send_row.addWidget(self.btn_send)
        send_row.addWidget(self.btn_clear_messages)

        right_layout.addLayout(receiver_row)
        right_layout.addWidget(self.text_messages)
        right_layout.addLayout(send_row)

        split.addWidget(left_box, 1)
        split.addWidget(right_box, 3)

        root.addLayout(split)
        self._set_connected_state(False)

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

    def _bind_signals(self) -> None:
        self.btn_reload_session.clicked.connect(lambda: self._load_saved_session(show_message=True, session_name=self._get_selected_profile()))
        self.btn_connect.clicked.connect(self._on_connect_requested)
        self.btn_disconnect.clicked.connect(self._on_disconnect_requested)
        self.btn_advanced.clicked.connect(self._open_advanced_popup)
        self.btn_send.clicked.connect(self._on_send)
        self.btn_load_history.clicked.connect(self._on_history)
        self.btn_clear_messages.clicked.connect(self._on_clear_messages)
        self.btn_refresh_presence.clicked.connect(self._on_presence)
        self.list_presence.itemClicked.connect(self._on_presence_item_clicked)
        self.btn_refresh_profiles.clicked.connect(self._populate_profiles)
        self.combo_profiles.activated.connect(self._on_profile_switched)
        self.chk_show_raw_presence.stateChanged.connect(lambda _: None)

    def _on_profile_switched(self, _: int) -> None:
        self._load_saved_session(show_message=False, session_name=self._get_selected_profile())
        profile = self.combo_profiles.currentText().strip() or "default"
        QMessageBox.information(self, "Chat", f"Profile switched to: {profile}")

    def _open_advanced_popup(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Advanced Chat Settings")
        dialog.resize(520, 180)

        root = QVBoxLayout(dialog)
        form = QFormLayout()

        ws_edit = QLineEdit(self.edit_ws_url.text().strip() or WS_URL_DEFAULT, dialog)
        profile_combo = QComboBox(dialog)
        for i in range(self.combo_profiles.count()):
            profile_combo.addItem(self.combo_profiles.itemText(i), self.combo_profiles.itemData(i))
        if self.combo_profiles.currentIndex() >= 0:
            profile_combo.setCurrentIndex(self.combo_profiles.currentIndex())

        raw_chk = QCheckBox("Show raw presence logs", dialog)
        raw_chk.setChecked(self.chk_show_raw_presence.isChecked())
        session_lbl = QLabel(self.lbl_session.text(), dialog)
        session_lbl.setWordWrap(True)

        form.addRow("WebSocket URL", ws_edit)
        form.addRow("Profile", profile_combo)
        form.addRow("", raw_chk)
        form.addRow("Session", session_lbl)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply,
            parent=dialog,
        )
        btn_reload = QPushButton("Reload Session", dialog)
        buttons.addButton(btn_reload, QDialogButtonBox.ButtonRole.ActionRole)
        root.addWidget(buttons)

        def _apply_settings(show_popup: bool = False) -> None:
            self.edit_ws_url.setText(ws_edit.text().strip() or WS_URL_DEFAULT)
            self.chk_show_raw_presence.setChecked(raw_chk.isChecked())

            selected = profile_combo.currentData()
            idx = self.combo_profiles.findData(selected)
            if idx >= 0:
                self.combo_profiles.setCurrentIndex(idx)
            self._load_saved_session(show_message=show_popup, session_name=self._get_selected_profile())
            session_lbl.setText(self.lbl_session.text())

        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(lambda: _apply_settings(show_popup=True))
        btn_reload.clicked.connect(lambda: _apply_settings(show_popup=True))
        buttons.accepted.connect(lambda: (_apply_settings(show_popup=False), dialog.accept()))
        buttons.rejected.connect(dialog.reject)

        dialog.exec()

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
        QMessageBox.information(self, "Chat", "Connecting to chat server...")
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
            QMessageBox.information(self, "Chat", "Disconnect requested.")
            self._stomp_worker.stop(manual=True)

    def _on_chat_connected(self) -> None:
        self.lbl_status.setText("Connected")
        self._set_connected_state(True)
        self._append_system("WebSocket/STOMP connected.")
        QMessageBox.information(self, "Chat", "Connected successfully.")
        if self._stomp_worker:
            self._stomp_worker.request_presence()

    def _on_chat_disconnected(self, reason: str) -> None:
        self.lbl_status.setText(reason)
        self._set_connected_state(False)
        self._append_system(reason)

    def _on_chat_error(self, message: str) -> None:
        self.lbl_status.setText("Connection error")
        self._set_connected_state(False)
        self._append_system(f"Connection error: {message}")

    def _on_functional_error(self, message: str) -> None:
        self._append_system(f"Server error: {message}")

    def _on_worker_finished(self) -> None:
        self._stomp_worker = None
        self._set_connected_state(False)

    def _get_receiver(self) -> str:
        data = self.combo_receiver.currentData()
        if data:
            return str(data).strip()
        return self.combo_receiver.currentText().strip()

    def _on_send(self) -> None:
        if not self._stomp_worker:
            QMessageBox.warning(self, "Chat", "Not connected.")
            return
        receiver = self._get_receiver()
        text = self.edit_message.text().strip()
        if not receiver or not text:
            return
        self._stomp_worker.send_private(receiver, text)
        self.edit_message.clear()

    def _on_history(self) -> None:
        if not self._stomp_worker:
            QMessageBox.warning(self, "Chat", "Not connected.")
            return
        receiver = self._get_receiver()
        if not receiver:
            return
        self._stomp_worker.request_history(receiver)

    def _on_presence(self) -> None:
        if self._stomp_worker:
            self._stomp_worker.request_presence()
        else:
            QMessageBox.warning(self, "Chat", "Connect first to refresh online users.")

    def _on_clear_messages(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Chat",
            "Clear all messages from this view?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.text_messages.clear()
            QMessageBox.information(self, "Chat", "Messages cleared.")

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
        current_receiver = self._get_receiver()
        self.combo_receiver.clear()
        if isinstance(users, list) and len(users) == 1 and isinstance(users[0], dict) and "onlineUsers" in users[0]:
            entries = users[0]["onlineUsers"]
        elif isinstance(users, dict) and "onlineUsers" in users:
            entries = users["onlineUsers"]
        else:
            entries = users if isinstance(users, list) else [users]

        if self.chk_show_raw_presence.isChecked():
            self._append_system(f"Presence snapshot raw: {entries}")

        my = (self._user_id or "").strip().lower()
        added: set[str] = set()
        for e in entries:
            if isinstance(e, dict):
                ident = (str(e.get("userId") or e.get("email") or e.get("username") or e.get("id") or e)).strip().lower()
                disp = str(e.get("userId") or e.get("email") or e.get("username") or e.get("id") or e)
            else:
                ident = str(e).strip().lower()
                disp = str(e)
            if not ident:
                continue

            list_item = QListWidgetItem(disp)
            list_item.setData(Qt.ItemDataRole.UserRole, ident)
            if my and ident == my:
                list_item.setText(f"{disp} (you)")
            else:
                if ident not in added:
                    self.combo_receiver.addItem(disp, ident)
                    added.add(ident)
            self.list_presence.addItem(list_item)

        if current_receiver:
            idx = self.combo_receiver.findData(current_receiver.strip().lower())
            if idx >= 0:
                self.combo_receiver.setCurrentIndex(idx)
            else:
                self.combo_receiver.setEditText(current_receiver)

    def _on_presence_update(self, payload: dict) -> None:
        user = str(payload.get("userId") or payload.get("email") or "unknown")
        status = str(payload.get("status") or payload.get("event") or "update")
        self._append_system(f"Presence: {user} -> {status}")

    def _on_presence_item_clicked(self, item: QListWidgetItem) -> None:
        receiver = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if not receiver or receiver == (self._user_id or "").strip().lower():
            return
        idx = self.combo_receiver.findData(receiver)
        if idx >= 0:
            self.combo_receiver.setCurrentIndex(idx)
        else:
            self.combo_receiver.setEditText(receiver)

    def _append_system(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.text_messages.append(f"[{ts}] [system] {text}")

    @staticmethod
    def _format_timestamp(raw: Any) -> str:
        from datetime import datetime as _dt
        if not raw:
            return _dt.now().strftime("%H:%M:%S")
        try:
            s = str(raw).strip()
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'
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

