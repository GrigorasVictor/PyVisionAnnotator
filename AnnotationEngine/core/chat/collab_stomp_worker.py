"""STOMP worker for annotation collaboration events.

Background thread managing STOMP subscriptions to collab topics, deduplicates incoming events,
routes payloads, sends outbound annotation events. Max send 256KB/frame to avoid proxy timeouts.
Key: set_active_session, send_event (queue), _route_message (dedup via eventId), 
_open_connection (CONNECT+SUBSCRIBE), run (recv loop + reconnect with backoff).
"""
from __future__ import annotations

import importlib
import json
import queue
import socket
import time
from typing import Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core.chat.collab_protocol import COLLAB_DEST_SEND_EVENT, COLLAB_TOPIC_SESSIONS


_MAX_SEND_BODY_BYTES = 256 * 1024


class CollabStompWorker(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal(str)
    connection_error = pyqtSignal(str)
    event_received = pyqtSignal(dict)
    debug_log = pyqtSignal(str)

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
        self._seen_event_ids: set[str] = set()
        self._active_session_id: str = ""

    def stop(self, manual: bool = True) -> None:
        self._manual_stop = manual
        self._stop_requested = True
        self._commands.put(("disconnect", {}))

    def set_active_session(self, session_id: str) -> None:
        self._commands.put(("set_session", {"sessionId": str(session_id).strip()}))

    def send_event(self, envelope: dict[str, Any]) -> None:
        self._commands.put(("send_event", envelope))

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
        if "\r\n\r\n" in raw:
            head, body = raw.split("\r\n\r\n", 1)
        elif "\n\n" in raw:
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

    def _subscribe_base(self) -> None:
        self._send_frame(
            "SUBSCRIBE",
            headers={
                "id": "collab-global",
                "destination": COLLAB_TOPIC_SESSIONS,
                "ack": "auto",
            },
        )
        self.debug_log.emit(f"STOMP SUBSCRIBE id=collab-global dest={COLLAB_TOPIC_SESSIONS}")

    def _subscribe_session(self, session_id: str) -> None:
        sid = str(session_id).strip()
        if not sid:
            return
        self._send_frame(
            "SUBSCRIBE",
            headers={
                "id": f"collab-sess-{sid}",
                "destination": f"{COLLAB_TOPIC_SESSIONS}/{sid}",
                "ack": "auto",
            },
        )
        self.debug_log.emit(f"STOMP SUBSCRIBE id=collab-sess-{sid} dest={COLLAB_TOPIC_SESSIONS}/{sid}")
        self._active_session_id = sid

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
                self._subscribe_base()
                if self._active_session_id:
                    self._subscribe_session(self._active_session_id)
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
            if cmd == "set_session":
                sid = str(payload.get("sessionId") or "").strip()
                if sid:
                    self._subscribe_session(sid)
                continue
            if cmd == "send_event":
                body = json.dumps(payload, ensure_ascii=True)
                body_bytes = len(body.encode("utf-8"))
                etype = str(payload.get("type") or "")
                sid = str(payload.get("sessionId") or "")

                # Large frames can trigger server/proxy closes; skip instead of forcing reconnect loops.
                if body_bytes > _MAX_SEND_BODY_BYTES:
                    self.debug_log.emit(
                        f"DROP SEND too_large bytes={body_bytes} max={_MAX_SEND_BODY_BYTES} type={etype} sessionId={sid}"
                    )
                    continue

                self._send_frame(
                    "SEND",
                    headers={
                        "destination": COLLAB_DEST_SEND_EVENT,
                        "content-type": "application/json",
                        "content-length": str(body_bytes),
                    },
                    body=body,
                )
                self.debug_log.emit(
                    f"STOMP SEND dest={COLLAB_DEST_SEND_EVENT} type={etype} sessionId={sid} bytes={body_bytes}"
                )

    def _route_message(self, body: str, headers: dict[str, str] | None = None) -> None:
        if not body:
            return
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body}
        if not isinstance(payload, dict):
            return
        destination = str((headers or {}).get("destination") or "").strip()
        if destination:
            payload.setdefault("_wsDestination", destination)
        eid = str(payload.get("eventId") or "").strip()
        if eid:
            if eid in self._seen_event_ids:
                return
            self._seen_event_ids.add(eid)
            if len(self._seen_event_ids) > 2048:
                # Keep memory bounded.
                self._seen_event_ids = set(list(self._seen_event_ids)[-1024:])
        self.event_received.emit(payload)

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

                    if not raw or raw.strip() == "":
                        continue
                    command, _headers, body = self._parse_frame(raw)
                    if command == "MESSAGE":
                        self._route_message(body, _headers)
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

