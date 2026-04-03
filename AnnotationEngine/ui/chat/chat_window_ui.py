"""UI construction helpers for ChatWindow."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from core.chat.chat_protocol import HTTP_BASE_DEFAULT, WS_URL_DEFAULT
from core.chat.collab_protocol import COLLAB_HTTP_BASE_DEFAULT


def build_chat_ui(window) -> None:
    root = QVBoxLayout(window)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(8)

    base_default = window._load_server_base_default()
    window._collab_ws_url = window._load_collab_ws_default(base_default)

    window.edit_ws_url = QLineEdit(window._load_chat_ws_default(base_default))
    window.edit_ws_url.setPlaceholderText(WS_URL_DEFAULT)
    window.edit_base_url = QLineEdit(base_default)
    window.edit_base_url.setPlaceholderText(HTTP_BASE_DEFAULT)
    window.lbl_session = QLabel("No saved session")
    window.combo_profiles = QComboBox()
    window.btn_refresh_profiles = QPushButton("Refresh Profiles")
    window.chk_show_raw_presence = QCheckBox("Show raw presence")

    window.btn_reload_session = QPushButton("Reload Session")
    window.btn_connect = QPushButton("Connect")
    window.btn_disconnect = QPushButton("Disconnect")
    window.btn_advanced = QPushButton("Advanced")

    window.combo_collab_sessions = QComboBox()
    window.combo_collab_sessions.setEditable(False)
    window.btn_collab_refresh = QPushButton("Load Sessions")
    window.btn_collab_create = QPushButton("Create Session")
    window.btn_collab_join = QPushButton("Join Session")
    toolbar = QFrame(window)
    toolbar.setObjectName("chatToolbar")
    toolbar_layout = QHBoxLayout(toolbar)
    toolbar_layout.setContentsMargins(10, 8, 10, 8)
    toolbar_layout.setSpacing(8)
    window.lbl_server = QLabel("Server:")
    window.lbl_identity = QLabel("Identity:")
    toolbar_layout.addWidget(window.lbl_server)
    toolbar_layout.addWidget(window.edit_ws_url, 2)
    toolbar_layout.addWidget(window.lbl_identity)
    toolbar_layout.addWidget(window.combo_profiles, 1)
    toolbar_layout.addWidget(window.btn_refresh_profiles)
    toolbar_layout.addWidget(window.btn_reload_session)
    toolbar_layout.addWidget(window.btn_connect)
    toolbar_layout.addWidget(window.btn_disconnect)
    toolbar_layout.addWidget(window.btn_advanced)
    root.addWidget(toolbar)

    collab_bar = QFrame(window)
    collab_layout = QHBoxLayout(collab_bar)
    collab_layout.setContentsMargins(10, 6, 10, 6)
    collab_layout.setSpacing(8)
    collab_layout.addWidget(QLabel("Session:"))
    collab_layout.addWidget(window.combo_collab_sessions, 1)
    collab_layout.addWidget(window.btn_collab_refresh)
    collab_layout.addWidget(window.btn_collab_create)
    collab_layout.addWidget(window.btn_collab_join)
    root.addWidget(collab_bar)

    info_row = QFrame(window)
    info_row.setObjectName("chatInfo")
    info_layout = QHBoxLayout(info_row)
    info_layout.setContentsMargins(10, 6, 10, 6)
    info_layout.setSpacing(8)
    window.lbl_status = QLabel("Not connected")
    info_layout.addWidget(window.lbl_status)
    info_layout.addStretch(1)
    info_layout.addWidget(window.chk_show_raw_presence)
    info_layout.addWidget(window.lbl_session)
    root.addWidget(info_row)

    window.lbl_server.setVisible(False)
    window.lbl_identity.setVisible(False)
    window.edit_ws_url.setVisible(False)
    window.edit_base_url.setVisible(False)
    window.combo_profiles.setVisible(False)
    window.btn_refresh_profiles.setVisible(False)
    window.btn_reload_session.setVisible(False)
    window.chk_show_raw_presence.setVisible(False)
    window.lbl_session.setVisible(False)
    info_row.setVisible(False)

    split = QHBoxLayout()
    split.setSpacing(8)

    left_box = QGroupBox("Online Users")
    left_layout = QVBoxLayout(left_box)
    window.list_presence = QListWidget()
    window.btn_refresh_presence = QPushButton("Refresh Presence")
    left_layout.addWidget(window.list_presence)
    left_layout.addWidget(window.btn_refresh_presence)

    right_box = QGroupBox("Conversation")
    right_layout = QVBoxLayout(right_box)

    receiver_row = QHBoxLayout()
    receiver_row.addWidget(QLabel("Chat with:"))
    window.combo_receiver = QComboBox()
    window.combo_receiver.setEditable(True)
    window.combo_receiver.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    window.combo_receiver.setPlaceholderText("Select user from left list")
    receiver_row.addWidget(window.combo_receiver)
    window.btn_load_history = QPushButton("Load History")
    receiver_row.addWidget(window.btn_load_history)

    from PyQt6.QtWidgets import QTextEdit

    window.text_messages = QTextEdit()
    window.text_messages.setReadOnly(True)

    send_row = QHBoxLayout()
    window.edit_message = QLineEdit()
    window.edit_message.setPlaceholderText("Type a private message...")
    window.btn_send = QPushButton("Send")
    window.btn_clear_messages = QPushButton("Clear Messages")
    send_row.addWidget(window.edit_message)
    send_row.addWidget(window.btn_send)
    send_row.addWidget(window.btn_clear_messages)

    right_layout.addLayout(receiver_row)
    right_layout.addWidget(window.text_messages)
    right_layout.addLayout(send_row)

    split.addWidget(left_box, 1)
    split.addWidget(right_box, 3)

    root.addLayout(split)
    window._set_connected_state(False)


def bind_chat_signals(window) -> None:
    window.btn_reload_session.clicked.connect(
        lambda: window._load_saved_session(show_message=True, session_name=window._get_selected_profile())
    )
    window.btn_connect.clicked.connect(window._on_connect_requested)
    window.btn_disconnect.clicked.connect(window._on_disconnect_requested)
    window.btn_advanced.clicked.connect(window._open_advanced_popup)
    window.btn_send.clicked.connect(window._on_send)
    window.btn_load_history.clicked.connect(window._on_history)
    window.btn_clear_messages.clicked.connect(window._on_clear_messages)
    window.btn_refresh_presence.clicked.connect(window._on_presence)
    window.list_presence.itemClicked.connect(window._on_presence_item_clicked)
    window.btn_refresh_profiles.clicked.connect(window._populate_profiles)
    window.combo_profiles.activated.connect(window._on_profile_switched)
    window.chk_show_raw_presence.stateChanged.connect(lambda _: None)
    window.btn_collab_refresh.clicked.connect(window._on_collab_refresh_sessions)
    window.btn_collab_create.clicked.connect(window._on_collab_create_session)
    window.btn_collab_join.clicked.connect(window._on_collab_join_session)


def open_advanced_popup(window) -> None:
    dialog = QDialog(window)
    dialog.setWindowTitle("Advanced Chat Settings")
    dialog.resize(520, 180)

    root = QVBoxLayout(dialog)
    form = QFormLayout()

    ws_edit = QLineEdit(window.edit_ws_url.text().strip() or WS_URL_DEFAULT, dialog)
    base_edit = QLineEdit(window.edit_base_url.text().strip() or COLLAB_HTTP_BASE_DEFAULT, dialog)
    profile_combo = QComboBox(dialog)
    for i in range(window.combo_profiles.count()):
        profile_combo.addItem(window.combo_profiles.itemText(i), window.combo_profiles.itemData(i))
    if window.combo_profiles.currentIndex() >= 0:
        profile_combo.setCurrentIndex(window.combo_profiles.currentIndex())

    raw_chk = QCheckBox("Show raw presence logs", dialog)
    raw_chk.setChecked(window.chk_show_raw_presence.isChecked())
    session_lbl = QLabel(window.lbl_session.text(), dialog)
    session_lbl.setWordWrap(True)

    form.addRow("WebSocket URL", ws_edit)
    form.addRow("HTTP Base URL", base_edit)
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
        window.edit_ws_url.setText(ws_edit.text().strip() or WS_URL_DEFAULT)
        window.edit_base_url.setText(base_edit.text().strip() or COLLAB_HTTP_BASE_DEFAULT)
        window.chk_show_raw_presence.setChecked(raw_chk.isChecked())
        window._persist_server_settings()

        selected = profile_combo.currentData()
        idx = window.combo_profiles.findData(selected)
        if idx >= 0:
            window.combo_profiles.setCurrentIndex(idx)
        window._load_saved_session(show_message=show_popup, session_name=window._get_selected_profile())
        session_lbl.setText(window.lbl_session.text())

    apply_btn = buttons.button(QDialogButtonBox.StandardButton.Apply)
    if apply_btn:
        apply_btn.clicked.connect(lambda: _apply_settings(show_popup=True))
    btn_reload.clicked.connect(lambda: _apply_settings(show_popup=True))
    buttons.accepted.connect(lambda: (_apply_settings(show_popup=False), dialog.accept()))
    buttons.rejected.connect(dialog.reject)

    dialog.exec()

