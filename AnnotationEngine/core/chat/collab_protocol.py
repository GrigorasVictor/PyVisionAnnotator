"""Protocol constants for annotation collaboration backend."""
from __future__ import annotations

COLLAB_HTTP_BASE_DEFAULT = "http://localhost"
COLLAB_WS_PATH = "/annotation/ws"
COLLAB_WS_URL_DEFAULT = f"ws://localhost{COLLAB_WS_PATH}"

COLLAB_SESSIONS_PATH = "/annotation/sessions"
COLLAB_UPLOAD_TEMP_PATH = "/annotation/media/upload-temp"
COLLAB_MEDIA_TEMP_PREFIX = "/annotation/media/temp"

COLLAB_DEST_SEND_EVENT = "/app/collab.event"
COLLAB_TOPIC_SESSIONS = "/topic/sessions"


