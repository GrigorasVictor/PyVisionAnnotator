# SYNC_ROUTES - ce face serverul concret + ce face clientul

Ghid scurt pentru integrarea frontend-ului cu backend-ul de colaborare realtime.

## IMPORTANT: rute prin Traefik (în setup-ul tău curent)

Pentru `annotation-service`, prefixul public este `/annotation`.

- REST list: `GET /annotation/sessions`
- REST snapshot: `GET /annotation/sessions/{sessionId}/snapshot`
- REST upload: `POST /annotation/media/upload-temp`
- REST download: `GET /annotation/media/temp/{imageId}?token=...`
- WS endpoint: `ws://localhost/annotation/ws`

Dacă folosești `ws://localhost/ws`, ajungi pe `chat-service` (nu pe `annotation-service`).

## 1) Ce ține serverul în memorie

Serverul păstrează in-memory, per `sessionId`:
- metadata sesiune (`projectId`, `imageId`, `cameraId`, `name`)
- useri + status (`ONLINE`/`OFFLINE`)
- adnotări (`id -> payload`), inclusiv `poly`, `rect`, `mask`
- `version` incremental per sesiune
- imagine temporară (`imageMeta` + bytes + token download)

La restart, datele se pierd (MVP).

---

## 2) Topic-uri WS care trebuie ascultate

- Global: `/topic/sessions`
  - primești: `session.created`, `session.updated`
- Cameră: `/topic/sessions/{sessionId}`
  - primești: `session.user.joined`, `session.user.left`
  - primești: `annotation.create`, `annotation.update`, `annotation.delete`
  - primești: `image.available`

Clientul trebuie să fie abonat la ambele topic-uri.

---

## 3) Flux concret: upload imagine

### Ce face clientul activ
1. face `POST /annotation/media/upload-temp` (multipart: `sessionId`, `projectId`, `imageId`, `cameraId`, `file`)

### Ce face serverul
1. validează fișierul imagine
2. creează/actualizează sesiunea (dacă e nevoie)
3. salvează bytes temporar + metadata (`downloadUrl` cu token)
4. emite în cameră (`/topic/sessions/{sessionId}`): `image.available`
5. emite global (`/topic/sessions`): `session.updated` cu `payload.reason = image_upload`
6. crește `version`

### Ce face clientul celălalt
1. primește `image.available`
2. citește `payload.downloadUrl`
3. descarcă imaginea de la `GET /annotation/media/temp/{imageId}?token=...`
4. actualizează canvasul

---

## 4) Flux concret: dacă userul pune un poly

### Ce trimite clientul
Pe `/app/collab.event`:

```json
{
  "eventId": "c1f4c9ea-26e1-4a68-8df2-b8f478b69102",
  "type": "annotation.create",
  "sessionId": "k7ylk",
  "projectId": "proj_alpha",
  "imageId": "img_0001",
  "cameraId": "cam_entrance_01",
  "payload": {
    "id": "ann_poly_001",
    "type": "poly",
    "label": "road",
    "color": "#3cb44b",
    "points": [[10.0, 20.0], [40.0, 22.0], [35.0, 60.0], [12.0, 55.0]],
    "x": 10.0,
    "y": 20.0,
    "w": 30.0,
    "h": 40.0,
    "version": 1
  }
}
```

### Ce face serverul
1. verifică membership user în sesiune
2. dedup pe `eventId` (ignore dacă duplicat)
3. pentru `annotation.create` / `annotation.update` -> `put(payload.id, payload)` în store in-memory
4. pentru `annotation.delete` -> `remove(payload.id)`
5. crește `version`
6. emite în cameră (`/topic/sessions/{sessionId}`) evenimentul normalizat (cu `actorId`, `version`, `timestamp`)
7. emite global (`/topic/sessions`) `session.updated` cu `reason = annotation`

### Ce face clientul remote
- la `annotation.create`/`update`: upsert în store local
- la `annotation.delete`: remove local
- re-render layer adnotări

---

## 5) Flux join/leave utilizator

Clientul trimite pe `/app/collab.event`:
- `type: session.user.joined`
- `type: session.user.left`

Serverul:
- actualizează status user
- emite în cameră event join/leave
- emite global `session.updated` (`reason = join` / `leave`)

---

## 6) Ce trebuie să facă frontend-ul corect (algoritm)

1. bootstrap:
   - `GET /annotation/sessions`
   - connect WS `ws://localhost/annotation/ws` cu JWT
   - subscribe `/topic/sessions`
2. la deschiderea camerei:
   - subscribe `/topic/sessions/{sessionId}`
   - `GET /annotation/sessions/{sessionId}/snapshot`
   - setează `lastVersionBySession[sessionId] = snapshot.version`
3. la fiecare WS event:
   - dacă `eventId` deja procesat -> ignore
   - dacă `event.version <= lastVersionBySession[sessionId]` -> ignore (stale)
   - altfel aplică event, update version, marchează `eventId`
4. la upload imagine:
   - folosește `image.available.payload.downloadUrl`
5. la reconnect:
   - reconnect WS + resubscribe
   - trimite `session.user.joined`
   - cere snapshot și reconciliază

---

## 7) Contract envelope WS (referință)

```json
{
  "eventId": "uuid",
  "type": "session.created | session.updated | annotation.create | annotation.update | annotation.delete | image.available | session.user.joined | session.user.left",
  "sessionId": "k7ylk",
  "projectId": "proj_alpha",
  "imageId": "img_0001",
  "cameraId": "cam_entrance_01",
  "actorId": "ana@gmail.com",
  "version": 46,
  "timestamp": "2026-04-03T16:05:00Z",
  "payload": {}
}
```

---

## 8) TL;DR

- Da, când urci poză, serverul o stochează temporar și anunță toți clienții prin `image.available`.
- Da, când pui `poly` (sau orice adnotare), serverul o salvează in-memory și o broadcast-ează automat în cameră.
- Dacă nu vezi loguri de `ws.event.in`/`annotation.*`, verifică primul lucru: să fie conectat WS la `ws://localhost/annotation/ws`, nu la `ws://localhost/ws`.
