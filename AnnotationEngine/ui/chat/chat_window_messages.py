"""Messaging and presence handlers for ChatWindow."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox


def get_receiver(window) -> str:
    data = window.combo_receiver.currentData()
    if data:
        return str(data).strip()
    return window.combo_receiver.currentText().strip()


def on_send(window) -> None:
    if not window._stomp_worker:
        QMessageBox.warning(window, "Chat", "Not connected.")
        return
    receiver = window._get_receiver()
    text = window.edit_message.text().strip()
    if not receiver or not text:
        return
    window._stomp_worker.send_private(receiver, text)
    window.edit_message.clear()


def on_history(window) -> None:
    if not window._stomp_worker:
        QMessageBox.warning(window, "Chat", "Not connected.")
        return
    receiver = window._get_receiver()
    if not receiver:
        return
    window._stomp_worker.request_history(receiver)


def on_presence(window) -> None:
    if window._stomp_worker:
        window._stomp_worker.request_presence()
    else:
        QMessageBox.warning(window, "Chat", "Connect first to refresh online users.")


def on_clear_messages(window) -> None:
    confirm = QMessageBox.question(
        window,
        "Chat",
        "Clear all messages from this view?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if confirm == QMessageBox.StandardButton.Yes:
        window.text_messages.clear()
        QMessageBox.information(window, "Chat", "Messages cleared.")


def on_private_message(window, payload: dict) -> None:
    sender = str(payload.get("senderId") or payload.get("senderDisplayName") or "unknown")
    message = str(payload.get("message") or "")
    ts = window._format_timestamp(payload.get("timestamp"))
    window.text_messages.append(f"[{ts}] {sender}: {message}")


def on_history_received(window, messages: list) -> None:
    window.text_messages.clear()
    for item in messages:
        if isinstance(item, dict):
            window._on_private_message(item)


def on_presence_snapshot(window, users: list) -> None:
    window.list_presence.clear()
    current_receiver = window._get_receiver()
    window.combo_receiver.clear()
    if isinstance(users, list) and len(users) == 1 and isinstance(users[0], dict) and "onlineUsers" in users[0]:
        entries = users[0]["onlineUsers"]
    elif isinstance(users, dict) and "onlineUsers" in users:
        entries = users["onlineUsers"]
    else:
        entries = users if isinstance(users, list) else [users]

    if window.chk_show_raw_presence.isChecked():
        window._append_system(f"Presence snapshot raw: {entries}")

    my = (window._user_id or "").strip().lower()
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
                window.combo_receiver.addItem(disp, ident)
                added.add(ident)
        window.list_presence.addItem(list_item)

    if current_receiver:
        idx = window.combo_receiver.findData(current_receiver.strip().lower())
        if idx >= 0:
            window.combo_receiver.setCurrentIndex(idx)
        else:
            window.combo_receiver.setEditText(current_receiver)


def on_presence_update(window, payload: dict) -> None:
    user = str(payload.get("userId") or payload.get("email") or "unknown")
    status = str(payload.get("status") or payload.get("event") or "update")
    window._append_system(f"Presence: {user} -> {status}")


def on_presence_item_clicked(window, item: QListWidgetItem) -> None:
    receiver = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
    if not receiver or receiver == (window._user_id or "").strip().lower():
        return
    idx = window.combo_receiver.findData(receiver)
    if idx >= 0:
        window.combo_receiver.setCurrentIndex(idx)
    else:
        window.combo_receiver.setEditText(receiver)


def append_system(window, text: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    window.text_messages.append(f"[{ts}] [system] {text}")


def format_timestamp(raw: Any) -> str:
    if not raw:
        return datetime.now().strftime("%H:%M:%S")
    try:
        s = str(raw).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        if "." in s:
            head, tail = s.split(".", 1)
            frac = tail
            tz = ""
            for sign in ("+", "-"):
                if sign in tail:
                    frac, tz = tail.split(sign, 1)
                    tz = sign + tz
                    break
            frac = (frac + "000000")[:6]
            s = head + "." + frac + tz
        dt = datetime.fromisoformat(s)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return datetime.now().strftime("%H:%M:%S")

