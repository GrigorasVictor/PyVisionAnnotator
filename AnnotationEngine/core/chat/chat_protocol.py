"""Chat protocol constants used by the standalone chat window."""
from __future__ import annotations

HTTP_BASE_DEFAULT = "http://localhost"
WS_URL_DEFAULT = "ws://localhost/ws"

AUTH_REGISTER_PATH = "/auth/register"
AUTH_LOGIN_PATH = "/auth/login"

APP_PREFIX = "/app"
DEST_SEND = f"{APP_PREFIX}/chat.send"
DEST_HISTORY = f"{APP_PREFIX}/chat.history"
DEST_PRESENCE = f"{APP_PREFIX}/chat.presence"

QUEUE_PRIVATE = "/user/queue/private"
QUEUE_HISTORY = "/user/queue/history"
QUEUE_PRESENCE = "/user/queue/presence"
QUEUE_ERRORS = "/user/queue/errors"
TOPIC_PRESENCE = "/topic/presence"

SUBSCRIPTIONS = (
    ("sub-private", QUEUE_PRIVATE),
    ("sub-history", QUEUE_HISTORY),
    ("sub-presence-me", QUEUE_PRESENCE),
    ("sub-errors", QUEUE_ERRORS),
    ("sub-presence-all", TOPIC_PRESENCE),
)

