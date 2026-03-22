"""STOMP-over-WebSocket worker used by the standalone chat window."""
from __future__ import annotations

import json
import importlib
import queue
import socket
import time
from typing import Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from core.chat.chat_protocol import (
    DEST_HISTORY,
    DEST_PRESENCE,
    DEST_SEND,
    QUEUE_ERRORS,
    QUEUE_HISTORY,
    QUEUE_PRESENCE,
    QUEUE_PRIVATE,
    SUBSCRIPTIONS,
    TOPIC_PRESENCE,
)


class ChatStompWorker(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal(str)
    connection_error = pyqtSignal(str)
    private_message = pyqtSignal(dict)
    history_received = pyqtSignal(list)
    presence_snapshot = pyqtSignal(list)
    presence_update = pyqtSignal(dict)
    functional_error = pyqtSignal(str)

    def __init__(self, ws_url: str, jwt_token: str, parent=None) -> None:
        super().__init__(parent)
        self._ws_url = ws_url
        self._jwt_token = jwt_token
        self._stop_requested = False
        self._manual_stop = False
        self._connected = False
        self._commands: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue()
        self._socket: Optional[Any] = None
        self._websocket_module: Any = None

    def stop(self, manual: bool = True) -> None:
        self._manual_stop = manual
        self._stop_requested = True
        self._commands.put(("disconnect", {}))

    def send_private(self, receiver_id: str, message: str) -> None:
        payload = {"receiverId": receiver_id, "message": message}
        self._commands.put(("send", payload))

    def request_history(self, receiver_id: str) -> None:
        payload = {"receiverId": receiver_id}
        self._commands.put(("history", payload))

    def request_presence(self) -> None:
        self._commands.put(("presence", {}))

    def _send_frame(self, command: str, headers: dict[str, str] | None = None, body: str = "") -> None:
        if not self._socket:
            return
        parts = [command]
        for key, value in (headers or {}).items():
            parts.append(f"{key}:{value}")
        parts.append("")
        parts.append(body)
        data = "\n".join(parts) + "\x00"
        self._socket.send(data)

    @staticmethod
    def _parse_frame(frame: str) -> tuple[str, dict[str, str], str]:
        raw = frame.rstrip("\x00")
        if "\n\n" in raw:
            head, body = raw.split("\n\n", 1)
        else:
            head, body = raw, ""
        lines = head.splitlines()
        command = lines[0].strip() if lines else ""
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
        return command, headers, body

    @staticmethod
    def _safe_json(raw: str) -> Any:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    def _open_connection(self) -> None:
        self._websocket_module = self._websocket_module or importlib.import_module("websocket")
        self._socket = self._websocket_module.WebSocket()
        self._socket.settimeout(1.0)
        auth_header = f"Authorization: Bearer {self._jwt_token}"
        self._socket.connect(self._ws_url, header=[auth_header])

        self._send_frame(
            "CONNECT",
            headers={
                "accept-version": "1.2",
                "host": "localhost",
                "Authorization": f"Bearer {self._jwt_token}",
            },
        )

        start = time.time()
        while time.time() - start < 8.0:
            try:
                raw = self._socket.recv()
            except self._websocket_module.WebSocketTimeoutException:
                continue
            command, _headers, _body = self._parse_frame(raw)
            if command == "CONNECTED":
                self._connected = True
                for sid, destination in SUBSCRIPTIONS:
                    self._send_frame(
                        "SUBSCRIBE",
                        headers={
                            "id": sid,
                            "destination": destination,
                            "ack": "auto",
                        },
                    )
                self.connected.emit()
                return
            if command == "ERROR":
                self.connection_error.emit("Server rejected STOMP CONNECT.")
                raise RuntimeError("STOMP CONNECT rejected")
        raise RuntimeError("Timed out waiting for STOMP CONNECTED frame")

    def _close_socket(self) -> None:
        sock = self._socket
        self._socket = None
        self._connected = False
        if not sock:
            return
        try:
            self._send_frame("DISCONNECT")
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

    def _route_message(self, destination: str, body: str) -> None:
        data = self._safe_json(body)
        if destination == QUEUE_PRIVATE:
            if isinstance(data, dict):
                self.private_message.emit(data)
            else:
                self.private_message.emit({"raw": str(data)})
            return
        if destination == QUEUE_HISTORY:
            if isinstance(data, list):
                self.history_received.emit(data)
            elif isinstance(data, dict):
                # Some backends wrap list in a payload key.
                messages = data.get("messages")
                if isinstance(messages, list):
                    self.history_received.emit(messages)
                else:
                    self.history_received.emit([data])
            else:
                self.history_received.emit([])
            return
        if destination == QUEUE_PRESENCE:
            if isinstance(data, list):
                self.presence_snapshot.emit(data)
            elif isinstance(data, dict):
                users = data.get("users")
                if isinstance(users, list):
                    self.presence_snapshot.emit(users)
                else:
                    self.presence_snapshot.emit([data])
            else:
                self.presence_snapshot.emit([])
            return
        if destination == TOPIC_PRESENCE:
            if isinstance(data, dict):
                self.presence_update.emit(data)
            return
        if destination == QUEUE_ERRORS:
            if isinstance(data, dict):
                message = str(data.get("message") or data.get("error") or data)
            else:
                message = str(data)
            self.functional_error.emit(message)

    def _process_commands(self) -> None:
        while True:
            try:
                cmd, payload = self._commands.get_nowait()
            except queue.Empty:
                return
            if cmd == "disconnect":
                self._stop_requested = True
                return
            if not self._connected:
                continue
            if cmd == "send":
                body = json.dumps(payload, ensure_ascii=True)
                self._send_frame(
                    "SEND",
                    headers={
                        "destination": DEST_SEND,
                        "content-type": "application/json",
                        "content-length": str(len(body.encode("utf-8"))),
                    },
                    body=body,
                )
            elif cmd == "history":
                body = json.dumps(payload, ensure_ascii=True)
                self._send_frame(
                    "SEND",
                    headers={
                        "destination": DEST_HISTORY,
                        "content-type": "application/json",
                        "content-length": str(len(body.encode("utf-8"))),
                    },
                    body=body,
                )
            elif cmd == "presence":
                self._send_frame(
                    "SEND",
                    headers={
                        "destination": DEST_PRESENCE,
                        "content-type": "application/json",
                        "content-length": "2",
                    },
                    body="{}",
                )

    def run(self) -> None:
        delay_seconds = 1.0
        while not self._stop_requested:
            try:
                self._open_connection()
                delay_seconds = 1.0
                while not self._stop_requested:
                    self._process_commands()
                    if not self._socket:
                        break
                    try:
                        raw = self._socket.recv()
                    except self._websocket_module.WebSocketTimeoutException:
                        continue
                    except (self._websocket_module.WebSocketConnectionClosedException, OSError, socket.error):
                        raise RuntimeError("WebSocket disconnected")

                    if not raw:
                        continue
                    # Brokers can send keepalive newlines, skip empty frames.
                    if raw.strip() == "":
                        continue
                    command, headers, body = self._parse_frame(raw)
                    if command == "MESSAGE":
                        self._route_message(headers.get("destination", ""), body)
                    elif command == "ERROR":
                        self.connection_error.emit("Received STOMP ERROR frame.")
                        raise RuntimeError("STOMP ERROR")
            except ModuleNotFoundError:
                self.connection_error.emit("Missing dependency: install 'websocket-client'.")
                self._stop_requested = True
            except Exception as exc:
                if self._stop_requested:
                    break
                self.connection_error.emit(str(exc))
            finally:
                self._close_socket()
                if not self._stop_requested:
                    self.disconnected.emit("Reconnecting...")

            if self._stop_requested:
                break
            time.sleep(delay_seconds)
            delay_seconds = min(delay_seconds * 2.0, 10.0)

        self._close_socket()
        reason = "Disconnected" if self._manual_stop else "Stopped"
        self.disconnected.emit(reason)


