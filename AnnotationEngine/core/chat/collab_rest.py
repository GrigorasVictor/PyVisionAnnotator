"""Small REST client for annotation collaboration endpoints."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from core.chat.collab_protocol import (
    COLLAB_MEDIA_TEMP_PREFIX,
    COLLAB_SESSIONS_PATH,
    COLLAB_UPLOAD_TEMP_PATH,
)


class CollabRestClient:
    def __init__(self, base_url: str, jwt_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._jwt_token = jwt_token

    def _json_request(self, method: str, path: str, data: bytes | None = None) -> tuple[int, dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self._jwt_token}",
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(
            url=f"{self._base_url}{path}",
            method=method,
            headers=headers,
            data=data,
        )
        try:
            with request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return resp.status, (json.loads(raw) if raw else {})
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                body = {"raw": raw}
            return exc.code, body

    def list_sessions(self) -> tuple[int, dict[str, Any]]:
        return self._json_request("GET", COLLAB_SESSIONS_PATH)

    def create_session(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        raw = json.dumps(payload or {}, ensure_ascii=True).encode("utf-8")
        return self._json_request("POST", COLLAB_SESSIONS_PATH, data=raw)

    def get_snapshot(self, session_id: str) -> tuple[int, dict[str, Any]]:
        sid = parse.quote(str(session_id).strip())
        return self._json_request("GET", f"{COLLAB_SESSIONS_PATH}/{sid}/snapshot")

    def upload_temp_image(
        self,
        *,
        session_id: str,
        project_id: str,
        image_id: str,
        camera_id: str,
        name: str = "",
        file_path: str,
    ) -> tuple[int, dict[str, Any]]:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return 0, {"error": f"Image not found: {file_path}"}

        boundary = f"----pyvision-{uuid.uuid4().hex}"
        fields = {
            "sessionId": str(session_id),
            "projectId": str(project_id),
            "imageId": str(image_id),
            "cameraId": str(camera_id),
        }
        if str(name).strip():
            fields["name"] = str(name).strip()

        form_parts: list[bytes] = []
        for k, v in fields.items():
            form_parts.append(f"--{boundary}\r\n".encode("utf-8"))
            form_parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
            form_parts.append(v.encode("utf-8"))
            form_parts.append(b"\r\n")

        mime = "image/jpeg"
        lower = path.suffix.lower()
        if lower == ".png":
            mime = "image/png"
        elif lower == ".bmp":
            mime = "image/bmp"

        file_bytes = path.read_bytes()
        form_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        form_parts.append(f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode("utf-8"))
        form_parts.append(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
        form_parts.append(file_bytes)
        form_parts.append(b"\r\n")
        form_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        payload = b"".join(form_parts)

        def _upload_with(path: str) -> tuple[int, dict[str, Any]]:
            req = request.Request(
                url=f"{self._base_url}{path}",
                method="POST",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._jwt_token}",
                    "Accept": "application/json",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Content-Length": str(len(payload)),
                },
            )
            try:
                with request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    return resp.status, (json.loads(raw) if raw else {})
            except error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    body_json = json.loads(raw) if raw else {}
                except Exception:
                    body_json = {"raw": raw}
                return exc.code, body_json

        status, body = _upload_with(COLLAB_UPLOAD_TEMP_PATH)
        return status, body

    def _download_temp_image_from_prefix(self, image_id: str, token: str, media_prefix: str) -> tuple[int, bytes, str]:
        iid = parse.quote(str(image_id).strip())
        q = parse.urlencode({"token": str(token)})
        url = f"{self._base_url}{media_prefix}/{iid}?{q}"
        req = request.Request(
            url=url,
            method="GET",
            headers={
                "Authorization": f"Bearer {self._jwt_token}",
                "Accept": "*/*",
            },
        )
        try:
            with request.urlopen(req, timeout=20) as resp:
                ct = str(resp.headers.get("Content-Type", ""))
                return resp.status, resp.read(), ct
        except error.HTTPError as exc:
            ct = str(exc.headers.get("Content-Type", ""))
            return exc.code, exc.read(), ct

    def download_temp_image(self, image_id: str, token: str) -> tuple[int, bytes, str]:
        return self._download_temp_image_from_prefix(image_id, token, COLLAB_MEDIA_TEMP_PREFIX)
