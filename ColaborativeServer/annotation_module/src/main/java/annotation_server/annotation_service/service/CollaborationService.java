package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.ImageMetaDto;
import annotation_server.annotation_service.dto.SessionItemDto;
import annotation_server.annotation_service.dto.SessionSnapshotDto;
import annotation_server.annotation_service.dto.SessionUserDto;
import annotation_server.annotation_service.dto.SessionsResponseDto;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.entity.SessionState;
import annotation_server.annotation_service.entity.SessionUserState;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class CollaborationService {

    private final Map<String, SessionState> sessionsById = new ConcurrentHashMap<>();
    private final TempImageStore tempImageStore;
    private final EventDedupStore eventDedupStore;

    public CollaborationService(TempImageStore tempImageStore, EventDedupStore eventDedupStore) {
        this.tempImageStore = tempImageStore;
        this.eventDedupStore = eventDedupStore;
    }

    public SessionState ensureSession(String sessionId, String projectId, String imageId, String cameraId, String name) {
        return sessionsById.computeIfAbsent(sessionId, id -> new SessionState(id, projectId, imageId, cameraId, name));
    }

    public SessionState getSession(String sessionId) {
        SessionState session = sessionsById.get(sessionId);
        if (session == null) {
            throw new NoSuchElementException("Session not found: " + sessionId);
        }
        return session;
    }

    public boolean isMember(String sessionId, String userId) {
        SessionState session = getSession(sessionId);
        return session.getUsers().containsKey(userId);
    }

    public void requireMember(String sessionId, String userId) {
        if (!isMember(sessionId, userId)) {
            throw new IllegalArgumentException("User is not a member of session: " + sessionId);
        }
    }

    public void markUser(String sessionId, String userId, String role, String status) {
        SessionState session = getSession(sessionId);
        Instant now = Instant.now();
        String displayName = deriveDisplayName(userId);
        session.getUsers().compute(userId, (k, existing) -> {
            if (existing == null) {
                return new SessionUserState(userId, displayName, role == null ? "EDITOR" : role, status, now, now);
            }
            existing.mark(status, now);
            return existing;
        });
        session.nextVersion(now);
    }

    public SessionsResponseDto listSessions() {
        List<SessionItemDto> items = sessionsById.values().stream()
                .sorted(Comparator.comparing(SessionState::getSessionId))
                .map(this::toItem)
                .toList();
        return new SessionsResponseDto(items, items.size());
    }

    public SessionSnapshotDto snapshot(String sessionId) {
        SessionState session = getSession(sessionId);
        List<Map<String, Object>> annotations = new ArrayList<>(session.getAnnotations().values());
        return new SessionSnapshotDto(
                session.getSessionId(),
                session.getProjectId(),
                session.getImageId(),
                session.getCameraId(),
                session.getName(),
                usersOf(session),
                annotations,
                tempImageStore.getMeta(session.getImageId()).orElse(null),
                session.getVersion()
        );
    }

    public WsEventEnvelope applyAnnotationEvent(WsEventEnvelope incoming, String actorId) {
        requireMember(incoming.sessionId(), actorId);
        if (eventDedupStore.isDuplicate(incoming.eventId())) {
            return null;
        }

        SessionState session = getSession(incoming.sessionId());
        Instant now = Instant.now();
        String type = incoming.type();

        if (EventType.ANNOTATION_DELETE.value().equals(type)) {
            Object id = incoming.payload() == null ? null : incoming.payload().get("id");
            if (id != null) {
                session.getAnnotations().remove(String.valueOf(id));
            }
        } else {
            Object id = incoming.payload() == null ? null : incoming.payload().get("id");
            if (id == null) {
                throw new IllegalArgumentException("Annotation payload.id is required");
            }
            session.getAnnotations().put(String.valueOf(id), incoming.payload());
        }

        long version = session.nextVersion(now);
        return new WsEventEnvelope(
                incoming.eventId(),
                type,
                incoming.sessionId(),
                session.getProjectId(),
                session.getImageId(),
                session.getCameraId(),
                actorId,
                version,
                now,
                incoming.payload()
        );
    }

    public WsEventEnvelope buildImageAvailableEvent(String sessionId, ImageMetaDto meta, String actorId) {
        SessionState session = getSession(sessionId);
        session.updateImage(meta.imageId(), meta.cameraId(), session.getName());
        long version = session.nextVersion(Instant.now());
        Map<String, Object> payload = Map.of(
                "fileName", meta.fileName(),
                "width", meta.width(),
                "height", meta.height(),
                "mimeType", meta.mimeType(),
                "sizeBytes", meta.sizeBytes(),
                "downloadUrl", meta.downloadUrl(),
                "expiresAt", meta.expiresAt().toString()
        );
        return new WsEventEnvelope(
                java.util.UUID.randomUUID().toString(),
                EventType.IMAGE_AVAILABLE.value(),
                sessionId,
                session.getProjectId(),
                meta.imageId(),
                meta.cameraId(),
                actorId,
                version,
                Instant.now(),
                payload
        );
    }

    private SessionItemDto toItem(SessionState session) {
        List<SessionUserDto> users = usersOf(session);
        int online = (int) users.stream().filter(u -> "ONLINE".equalsIgnoreCase(u.status())).count();
        return new SessionItemDto(
                session.getSessionId(),
                session.getProjectId(),
                session.getImageId(),
                session.getCameraId(),
                session.getName(),
                users,
                online,
                session.getLastEventAt(),
                session.getVersion()
        );
    }

    private List<SessionUserDto> usersOf(SessionState session) {
        return session.getUsers().values().stream()
                .map(u -> new SessionUserDto(
                        u.getUserId(),
                        u.getDisplayName(),
                        u.getStatus(),
                        u.getRole(),
                        u.getJoinedAt(),
                        u.getLastSeenAt()
                ))
                .sorted(Comparator.comparing(SessionUserDto::userId))
                .toList();
    }

    private String deriveDisplayName(String userId) {
        if (userId == null || userId.isBlank()) {
            return "unknown";
        }
        int at = userId.indexOf('@');
        return at > 0 ? userId.substring(0, at) : userId;
    }
}


