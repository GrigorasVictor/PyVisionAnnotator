package annotation_server.annotation_service.controller;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.ImageMetaDto;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.service.AnnotationChunkAssemblyService;
import annotation_server.annotation_service.service.CollaborationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.MessageExceptionHandler;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Controller;

import java.security.Principal;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Controller
public class CollaborationWsController {

    private static final Logger log = LoggerFactory.getLogger(CollaborationWsController.class);

    private final CollaborationService collaborationService;
    private final AnnotationChunkAssemblyService chunkAssemblyService;
    private final SimpMessagingTemplate messagingTemplate;

    public CollaborationWsController(CollaborationService collaborationService,
                                     AnnotationChunkAssemblyService chunkAssemblyService,
                                     SimpMessagingTemplate messagingTemplate) {
        this.collaborationService = collaborationService;
        this.chunkAssemblyService = chunkAssemblyService;
        this.messagingTemplate = messagingTemplate;
    }

    @MessageMapping("/collab.event")
    public void onEvent(@Payload WsEventEnvelope event, Principal principal) {
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            log.warn("ws.event.rejected reason=missing_principal");
            throw new AccessDeniedException("Missing principal");
        }
        if (event == null || event.sessionId() == null || event.sessionId().isBlank() || event.type() == null) {
            log.warn("ws.event.rejected reason=invalid_envelope actor={}", principal.getName());
            throw new IllegalArgumentException("Invalid event envelope");
        }
        String actor = principal.getName().toLowerCase();
        log.info("ws.event.in eventId={} type={} sessionId={} actor={}",
                event.eventId(),
                event.type(),
                event.sessionId(),
                actor);

        if (EventType.SESSION_USER_JOINED.value().equals(event.type())) {
            collaborationService.ensureSession(
                    event.sessionId(),
                    event.projectId(),
                    event.imageId(),
                    event.cameraId(),
                    event.sessionId()
            );
            collaborationService.markUser(event.sessionId(), actor, "EDITOR", "ONLINE");
            WsEventEnvelope out = new WsEventEnvelope(
                    event.eventId() == null ? UUID.randomUUID().toString() : event.eventId(),
                    EventType.SESSION_USER_JOINED.value(),
                    event.sessionId(),
                    event.projectId(),
                    event.imageId(),
                    event.cameraId(),
                    actor,
                    collaborationService.snapshot(event.sessionId()).version(),
                    java.time.Instant.now(),
                    Map.of("userId", actor)
            );
            messagingTemplate.convertAndSend("/topic/sessions/" + event.sessionId(), out);
            log.info("ws.event.out eventId={} type={} sessionId={} actor={} version={} destination={}",
                    out.eventId(),
                    out.type(),
                    out.sessionId(),
                    out.actorId(),
                    out.version(),
                    "/topic/sessions/" + out.sessionId());
            emitSessionUpdated(event.sessionId(), actor, "join");
            return;
        }

        if (EventType.SESSION_USER_LEFT.value().equals(event.type())) {
            collaborationService.requireMember(event.sessionId(), actor);
            collaborationService.markUser(event.sessionId(), actor, "EDITOR", "OFFLINE");
            WsEventEnvelope out = new WsEventEnvelope(
                    event.eventId() == null ? UUID.randomUUID().toString() : event.eventId(),
                    EventType.SESSION_USER_LEFT.value(),
                    event.sessionId(),
                    event.projectId(),
                    event.imageId(),
                    event.cameraId(),
                    actor,
                    collaborationService.snapshot(event.sessionId()).version(),
                    java.time.Instant.now(),
                    Map.of("userId", actor)
            );
            messagingTemplate.convertAndSend("/topic/sessions/" + event.sessionId(), out);
            log.info("ws.event.out eventId={} type={} sessionId={} actor={} version={} destination={}",
                    out.eventId(),
                    out.type(),
                    out.sessionId(),
                    out.actorId(),
                    out.version(),
                    "/topic/sessions/" + out.sessionId());
            emitSessionUpdated(event.sessionId(), actor, "leave");
            return;
        }

        if (EventType.IMAGE_AVAILABLE.value().equals(event.type())) {
            collaborationService.requireMember(event.sessionId(), actor);
            ImageMetaDto meta = imageMetaFromEvent(event);
            WsEventEnvelope out = collaborationService.buildImageAvailableEvent(event.sessionId(), meta, actor);
            messagingTemplate.convertAndSend("/topic/sessions/" + event.sessionId(), out);
            log.info("ws.event.out eventId={} type={} sessionId={} actor={} version={} destination={}",
                    out.eventId(),
                    out.type(),
                    out.sessionId(),
                    out.actorId(),
                    out.version(),
                    "/topic/sessions/" + out.sessionId());
            emitSessionUpdated(event.sessionId(), actor, "image_available");
            return;
        }

        boolean isChunk = EventType.ANNOTATION_CHUNK.value().equals(event.type());
        ChunkMeta chunkMeta = isChunk ? ChunkMeta.from(event) : null;

        WsEventEnvelope incomingForApply = event;
        if (isChunk) {
            try {
                collaborationService.requireMember(event.sessionId(), actor);
                incomingForApply = chunkAssemblyService.acceptChunk(event, actor);
                if (incomingForApply == null) {
                    return;
                }
                log.info("ws.chunk.reassembled chunkId={} originalType={} sessionId={} actor={}",
                        chunkMeta.chunkId,
                        incomingForApply.type(),
                        incomingForApply.sessionId(),
                        actor);
            } catch (RuntimeException ex) {
                 log.warn("ws.chunk.error chunkId={} sessionId={} actor={} code=chunk_invalid",
                        chunkMeta.chunkId,
                        event.sessionId(),
                        actor);
                sendChunkError(actor, event.sessionId(), chunkMeta, "chunk_invalid", ex.getMessage());
                return;
            }
        }

        WsEventEnvelope applied;
        try {
            collaborationService.requireMember(incomingForApply.sessionId(), actor);
            applied = collaborationService.applyAnnotationEvent(incomingForApply, actor);
        } catch (RuntimeException ex) {
            if (isChunk) {
                log.warn("ws.chunk.error chunkId={} sessionId={} actor={} code=chunk_apply_failed",
                        chunkMeta.chunkId,
                        incomingForApply.sessionId(),
                        actor);
                sendChunkError(actor, incomingForApply.sessionId(), chunkMeta, "chunk_apply_failed", ex.getMessage());
                return;
            }
            throw ex;
        }

        if (applied != null) {
            messagingTemplate.convertAndSend("/topic/sessions/" + incomingForApply.sessionId(), applied);
            log.info("ws.event.out eventId={} type={} sessionId={} actor={} version={} destination={}",
                    applied.eventId(),
                    applied.type(),
                    applied.sessionId(),
                    applied.actorId(),
                    applied.version(),
                    "/topic/sessions/" + applied.sessionId());
            emitSessionUpdated(incomingForApply.sessionId(), actor, "annotation");
            if (isChunk) {
                sendChunkAck(actor, incomingForApply.sessionId(), chunkMeta, applied.eventId(), applied.type(), false);
            }
        } else {
            log.info("ws.event.skipped reason=duplicate eventId={} type={} sessionId={} actor={}",
                    incomingForApply.eventId(),
                    incomingForApply.type(),
                    incomingForApply.sessionId(),
                    actor);
            if (isChunk) {
                sendChunkAck(actor, incomingForApply.sessionId(), chunkMeta, incomingForApply.eventId(), incomingForApply.type(), true);
            }
        }
    }

    private void sendChunkAck(String actor,
                              String sessionId,
                              ChunkMeta chunkMeta,
                              String eventId,
                              String originalType,
                              boolean duplicate) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("chunkId", chunkMeta == null ? null : chunkMeta.chunkId);
        payload.put("sessionId", sessionId);
        payload.put("originalType", originalType);
        payload.put("originalEventId", eventId);
        payload.put("total", chunkMeta == null ? null : chunkMeta.total);
        payload.put("duplicate", duplicate);
        WsEventEnvelope ack = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CHUNK_ACK.value(),
                sessionId,
                null,
                null,
                null,
                "system",
                0,
                Instant.now(),
                payload
        );
        messagingTemplate.convertAndSendToUser(actor, "/queue/collab.chunk", ack);
    }

    private void sendChunkError(String actor,
                                String sessionId,
                                ChunkMeta chunkMeta,
                                String code,
                                String message) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("chunkId", chunkMeta == null ? null : chunkMeta.chunkId);
        payload.put("sessionId", sessionId);
        payload.put("originalType", chunkMeta == null ? null : chunkMeta.originalType);
        payload.put("index", chunkMeta == null ? null : chunkMeta.index);
        payload.put("total", chunkMeta == null ? null : chunkMeta.total);
        payload.put("code", code);
        payload.put("message", message == null ? "Unknown chunk error" : message);
        WsEventEnvelope error = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CHUNK_ERROR.value(),
                sessionId,
                null,
                null,
                null,
                "system",
                0,
                Instant.now(),
                payload
        );
        messagingTemplate.convertAndSendToUser(actor, "/queue/collab.chunk", error);
    }

    @MessageExceptionHandler({IllegalArgumentException.class, AccessDeniedException.class})
    public void handleWsMessageException(Throwable ex, Principal principal) {
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            log.warn("ws.error.unhandled reason=missing_principal message={}", ex.getMessage());
            return;
        }
        String actor = principal.getName().toLowerCase();
        Map<String, Object> payload = new HashMap<>();
        payload.put("code", ex instanceof AccessDeniedException ? "access_denied" : "bad_request");
        payload.put("message", ex.getMessage() == null ? "Unknown websocket error" : ex.getMessage());
        WsEventEnvelope error = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.WS_ERROR.value(),
                null,
                null,
                null,
                null,
                "system",
                0,
                Instant.now(),
                payload
        );
        messagingTemplate.convertAndSendToUser(actor, "/queue/collab.errors", error);
        log.warn("ws.error.out actor={} code={}",
                actor,
                payload.get("code"));
    }

    private void emitSessionUpdated(String sessionId, String actor, String reason) {
        WsEventEnvelope sessionUpdated = collaborationService.buildSessionListEvent(
                EventType.SESSION_UPDATED.value(),
                sessionId,
                actor,
                reason
        );
        messagingTemplate.convertAndSend("/topic/sessions", sessionUpdated);
        log.info("ws.event.out eventId={} type={} sessionId={} actor={} version={} destination={}",
                sessionUpdated.eventId(),
                sessionUpdated.type(),
                sessionUpdated.sessionId(),
                sessionUpdated.actorId(),
                sessionUpdated.version(),
                "/topic/sessions");
    }

    private ImageMetaDto imageMetaFromEvent(WsEventEnvelope event) {
        Map<String, Object> payload = event.payload() == null ? Map.of() : event.payload();
        String imageId = stringValue(payload.get("imageId"));
        if (imageId == null || imageId.isBlank()) {
            imageId = event.imageId();
        }
        if (imageId == null || imageId.isBlank()) {
            throw new IllegalArgumentException("image.available requires imageId in envelope or payload");
        }

        String cameraId = stringValue(payload.get("cameraId"));
        if (cameraId == null || cameraId.isBlank()) {
            cameraId = event.cameraId();
        }

        String expiresAtRaw = stringValue(payload.get("expiresAt"));
        Instant expiresAt = expiresAtRaw == null || expiresAtRaw.isBlank()
                ? Instant.now().plusSeconds(3600)
                : Instant.parse(expiresAtRaw);

        return new ImageMetaDto(
                event.sessionId(),
                imageId,
                cameraId,
                defaultString(stringValue(payload.get("fileName")), imageId),
                defaultString(stringValue(payload.get("mimeType")), "application/octet-stream"),
                longValue(payload.get("sizeBytes"), 0L),
                intValue(payload.get("width"), 0),
                intValue(payload.get("height"), 0),
                stringValue(payload.get("checksumSha256")),
                defaultString(stringValue(payload.get("downloadUrl")), ""),
                expiresAt
        );
    }

    private String stringValue(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private String defaultString(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            return Integer.parseInt(text);
        }
        return fallback;
    }

    private long longValue(Object value, long fallback) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            return Long.parseLong(text);
        }
        return fallback;
    }

    private static final class ChunkMeta {
        private final String chunkId;
        private final String originalType;
        private final Integer index;
        private final Integer total;

        private ChunkMeta(String chunkId, String originalType, Integer index, Integer total) {
            this.chunkId = chunkId;
            this.originalType = originalType;
            this.index = index;
            this.total = total;
        }

        private static ChunkMeta from(WsEventEnvelope event) {
            if (event == null || event.payload() == null) {
                return new ChunkMeta(null, null, null, null);
            }
            Object rawIndex = event.payload().get("index");
            Object rawTotal = event.payload().get("total");
            Integer index = rawIndex instanceof Number number ? number.intValue() : null;
            Integer total = rawTotal instanceof Number number ? number.intValue() : null;
            return new ChunkMeta(
                    event.payload().get("chunkId") == null ? null : String.valueOf(event.payload().get("chunkId")),
                    event.payload().get("originalType") == null ? null : String.valueOf(event.payload().get("originalType")),
                    index,
                    total
            );
        }
    }
}


