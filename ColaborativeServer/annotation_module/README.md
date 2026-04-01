# Annotation Module Realtime Collaboration (In-Memory MVP)

This module now provides a hybrid collaboration backend:
- REST for bootstrap/list/recovery
- WebSocket STOMP for live sync
- in-memory stores only (data is lost on restart)

## Implemented APIs

- `GET /sessions`
- `GET /sessions/{sessionId}/snapshot`
- `POST /media/upload-temp` (multipart)
- `GET /media/temp/{imageId}?token=...`
- WS endpoint: `/ws`
- WS app destination: `/app/collab.event`
- WS topic destination: `/topic/sessions/{sessionId}`

## Security

- JWT required for REST (`Authorization: Bearer ...`)
- JWT required for WebSocket handshake (header or `?token=`)

## In-memory stores

- `sessionsById`
- `annotations` per session
- `presence/users` per session
- `temp image metadata + bytes`
- `processedEventIds` with TTL

## Config

In `application.properties`:
- `jwt.secret`
- `collab.media-ttl`
- `collab.event-dedup-ttl`
- `collab.cleanup-interval-ms`

## Run tests

```powershell
Set-Location "C:\Stuff\Scoala\Licienta\ColaborativeServer\annotation_module"
.\mvnw.cmd test
```

