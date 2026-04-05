package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.ImageMetaDto;
import annotation_server.annotation_service.dto.CreateSessionResponseDto;
import annotation_server.annotation_service.dto.SessionItemDto;
import annotation_server.annotation_service.dto.SessionSnapshotDto;
import annotation_server.annotation_service.dto.SessionUserDto;
import annotation_server.annotation_service.dto.SessionsResponseDto;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.entity.SessionState;
import annotation_server.annotation_service.entity.SessionUserState;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class CollaborationService {

    private static final Logger log = LoggerFactory.getLogger(CollaborationService.class);
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private static final String SESSION_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789";
    private static final int SESSION_CODE_LENGTH = 5;

    private final Map<String, SessionState> sessionsById = new ConcurrentHashMap<>();
    private final TempImageStore tempImageStore;
    private final EventDedupStore eventDedupStore;
    private final Duration emptySessionTtl;
    private final int maxMaskDataChars;

    public CollaborationService(TempImageStore tempImageStore,
                                EventDedupStore eventDedupStore,
                                @Value("${collab.empty-session-ttl:PT5M}") Duration emptySessionTtl,
                                @Value("${collab.mask-max-data-chars:2000000}") int maxMaskDataChars) {
        this.tempImageStore = tempImageStore;
        this.eventDedupStore = eventDedupStore;
        this.emptySessionTtl = emptySessionTtl;
        this.maxMaskDataChars = maxMaskDataChars;
    }

    public CreateSessionResponseDto createSession(String projectId,
                                                  String imageId,
                                                  String cameraId,
                                                  String name,
                                                  String creatorUserId) {
        String sessionCode = generateUniqueSessionCode();
        String normalizedProjectId = blankToDefault(projectId, "proj_" + sessionCode);
        String normalizedImageId = blankToDefault(imageId, "img_" + sessionCode);
        String normalizedCameraId = blankToDefault(cameraId, "cam_" + sessionCode);
        String normalizedName = blankToDefault(name, "Room " + sessionCode);

        ensureSession(sessionCode, normalizedProjectId, normalizedImageId, normalizedCameraId, normalizedName);

        if (creatorUserId != null && !creatorUserId.isBlank()) {
            markUser(sessionCode, creatorUserId.toLowerCase(), "EDITOR", "ONLINE");
        }

        log.info("session.created sessionId={} projectId={} imageId={} cameraId={} actor={}",
                sessionCode,
                normalizedProjectId,
                normalizedImageId,
                normalizedCameraId,
                creatorUserId == null ? "" : creatorUserId.toLowerCase());

        return new CreateSessionResponseDto(
                sessionCode,
                normalizedProjectId,
                normalizedImageId,
                normalizedCameraId,
                normalizedName
        );
    }

    public SessionState ensureSession(String sessionId, String projectId, String imageId, String cameraId, String name) {
        return sessionsById.computeIfAbsent(sessionId, id -> {
            log.info("session.bootstrap sessionId={} projectId={} imageId={} cameraId={} name={}",
                    id,
                    projectId,
                    imageId,
                    cameraId,
                    name);
            return new SessionState(id, projectId, imageId, cameraId, name);
        });
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
        return session.getUsers().containsKey(normalizeUserId(userId));
    }

    public void requireMember(String sessionId, String userId) {
        if (!isMember(sessionId, userId)) {
            log.warn("membership.denied sessionId={} userId={}", sessionId, normalizeUserId(userId));
            throw new IllegalArgumentException("User is not a member of session: " + sessionId);
        }
    }

    public void ensureMember(String sessionId, String userId, String role, String status) {
        String normalizedUserId = normalizeUserId(userId);
        if (normalizedUserId.isBlank()) {
            return;
        }
        SessionState session = getSession(sessionId);
        if (!session.getUsers().containsKey(normalizedUserId)) {
            markUser(sessionId, normalizedUserId, role, status);
        }
    }

    public void markUser(String sessionId, String userId, String role, String status) {
        SessionState session = getSession(sessionId);
        Instant now = Instant.now();
        String normalizedUserId = normalizeUserId(userId);
        String displayName = deriveDisplayName(normalizedUserId);
        session.getUsers().compute(normalizedUserId, (k, existing) -> {
            if (existing == null) {
                return new SessionUserState(normalizedUserId, displayName, role == null ? "EDITOR" : role, status, now, now);
            }
            existing.mark(status, now);
            return existing;
        });
        long version = session.nextVersion(now);
        log.info("session.user.marked sessionId={} userId={} status={} role={} version={}",
                sessionId,
                normalizedUserId,
                status,
                role == null ? "EDITOR" : role,
                version);
    }

    public SessionsResponseDto listSessions() {
        List<SessionItemDto> items = sessionsById.values().stream()
                .sorted(Comparator.comparing(SessionState::getSessionId))
                .map(this::toItem)
                .toList();
        log.info("sessions.list total={}", items.size());
        return new SessionsResponseDto(items, items.size());
    }

    public SessionItemDto sessionItem(String sessionId) {
        return toItem(getSession(sessionId));
    }

    public SessionSnapshotDto snapshot(String sessionId) {
        SessionState session = getSession(sessionId);
        List<Map<String, Object>> annotations = new ArrayList<>(session.getAnnotations().values());
        log.info("session.snapshot sessionId={} users={} annotations={} version={}",
                sessionId,
                session.getUsers().size(),
                annotations.size(),
                session.getVersion());
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
            log.info("annotation.event.duplicate eventId={} type={} sessionId={} actor={}",
                    incoming.eventId(),
                    incoming.type(),
                    incoming.sessionId(),
                    actorId);
            return null;
        }

        SessionState session = getSession(incoming.sessionId());
        Instant now = Instant.now();
        String type = incoming.type();

        if (EventType.ANNOTATION_DELETE.value().equals(type)) {
            Object id = incoming.payload() == null ? null : incoming.payload().get("id");
            if (id != null) {
                session.getAnnotations().remove(String.valueOf(id));
                log.info("annotation.delete sessionId={} actor={} annotationId={}", incoming.sessionId(), actorId, id);
            }
            // TODO delete: temporary payload visibility for client-side debugging.
            log.info("annotation.payload.tmp eventId={} type={} sessionId={} actor={} payloadJson={}",
                    incoming.eventId(),
                    type,
                    incoming.sessionId(),
                    actorId,
                    toJson(incoming.payload()));
        } else {
            // TODO delete: temporary payload visibility for client-side debugging.
            log.info("annotation.payload.tmp eventId={} type={} sessionId={} actor={} payloadJson={}",
                    incoming.eventId(),
                    type,
                    incoming.sessionId(),
                    actorId,
                    toJson(incoming.payload()));
            Map<String, Object> payload = validateAnnotationPayload(incoming.payload());
            Object id = payload.get("id");
            session.getAnnotations().put(String.valueOf(id), payload);


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

    private Map<String, Object> validateAnnotationPayload(Map<String, Object> payload) {
        if (payload == null) {
            throw new IllegalArgumentException("Annotation payload is required");
        }

        String id = requireNonBlankString(payload, "id");
        String type = requireNonBlankString(payload, "type");

        if ("mask".equals(type)) {
            Map<?, ?> maskMap = payload.get("mask") instanceof Map<?, ?> map ? map : Map.of();
            Object points = maskMap.containsKey("points") ? maskMap.get("points") : payload.get("points");

            if (points == null) {
                throw new IllegalArgumentException("Mask annotation requires points (payload.points or payload.mask.points)");
            }
            validateMaskPoints(points);

            log.debug("annotation.mask.validated id={} pointsOnly=true", id);
        }

        return payload;
    }

    private String requireNonBlankString(Map<?, ?> source, String key) {
        return requireNonBlankString(source, key, "payload." + key);
    }

    private String requireNonBlankString(Map<?, ?> source, String key, String fieldName) {
        Object value = source.get(key);
        if (!(value instanceof String text) || text.isBlank()) {
            throw new IllegalArgumentException(fieldName + " is required");
        }
        return text;
    }

    private void validateMaskPoints(Object pointsRaw) {
        if (!(pointsRaw instanceof List<?> points) || points.isEmpty()) {
            throw new IllegalArgumentException("payload.points must contain at least one [x, y] entry");
        }

        for (int i = 0; i < points.size(); i++) {
            Object pointRaw = points.get(i);
            if (!(pointRaw instanceof List<?> point) || point.size() != 2) {
                throw new IllegalArgumentException("payload.points[" + i + "] must contain exactly [x, y]");
            }
            validateFiniteNumber(point.get(0), "payload.points[" + i + "][0]");
            validateFiniteNumber(point.get(1), "payload.points[" + i + "][1]");
        }
    }

    private void validateFiniteNumber(Object value, String fieldName) {
        if (!(value instanceof Number number)) {
            throw new IllegalArgumentException(fieldName + " must be numeric");
        }
        double numericValue = number.doubleValue();
        if (Double.isNaN(numericValue) || Double.isInfinite(numericValue)) {
            throw new IllegalArgumentException(fieldName + " must be finite");
        }
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

    public WsEventEnvelope buildSessionListEvent(String type, String sessionId, String actorId, String reason) {
        SessionItemDto item = sessionItem(sessionId);
        Map<String, Object> payload = new ConcurrentHashMap<>();
        payload.put("reason", reason == null || reason.isBlank() ? "unknown" : reason);
        payload.put("session", item);

        return new WsEventEnvelope(
                java.util.UUID.randomUUID().toString(),
                type,
                item.sessionId(),
                item.projectId(),
                item.imageId(),
                item.cameraId(),
                actorId == null || actorId.isBlank() ? "system" : actorId,
                item.version(),
                Instant.now(),
                payload
        );
    }

    @Scheduled(fixedDelayString = "${collab.cleanup-interval-ms:60000}")
    public void cleanupInactiveSessions() {
        cleanupInactiveSessions(Instant.now());
    }

    void cleanupInactiveSessions(Instant now) {
        sessionsById.entrySet().removeIf(entry -> {
            boolean remove = isInactiveEmptySession(entry.getValue(), now);
            if (remove) {
                log.info("session.cleaned sessionId={} reason=inactive_empty ttl={}", entry.getKey(), emptySessionTtl);
            }
            return remove;
        });
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

    private boolean isInactiveEmptySession(SessionState session, Instant now) {
        boolean hasOnlineUsers = session.getUsers().values().stream()
                .anyMatch(user -> "ONLINE".equalsIgnoreCase(user.getStatus()));
        if (hasOnlineUsers) {
            return false;
        }
        return session.getLastEventAt().plus(emptySessionTtl).isBefore(now);
    }

    private String generateUniqueSessionCode() {
        for (int i = 0; i < 30; i++) {
            String code = randomSessionCode();
            if (!sessionsById.containsKey(code)) {
                return code;
            }
        }
        throw new IllegalStateException("Unable to allocate unique session code");
    }

    private String randomSessionCode() {
        StringBuilder builder = new StringBuilder(SESSION_CODE_LENGTH);
        for (int i = 0; i < SESSION_CODE_LENGTH; i++) {
            int index = ThreadLocalRandom.current().nextInt(SESSION_CODE_ALPHABET.length());
            builder.append(SESSION_CODE_ALPHABET.charAt(index));
        }
        return builder.toString();
    }

    private String blankToDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String deriveDisplayName(String userId) {
        if (userId == null || userId.isBlank()) {
            return "unknown";
        }
        int at = userId.indexOf('@');
        return at > 0 ? userId.substring(0, at) : userId;
    }

    private String normalizeUserId(String userId) {
        return userId == null ? "" : userId.trim().toLowerCase();
    }

    private String toJson(Object value) {
        if (value == null) {
            return "null";
        }
        try {
            return OBJECT_MAPPER.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            return String.valueOf(value);
        }
    }
}

