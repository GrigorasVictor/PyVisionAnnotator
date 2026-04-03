package annotation_server.annotation_service.controller;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.service.CollaborationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Controller;

import java.security.Principal;
import java.util.Map;
import java.util.UUID;

@Controller
public class CollaborationWsController {

    private static final Logger log = LoggerFactory.getLogger(CollaborationWsController.class);

    private final CollaborationService collaborationService;
    private final SimpMessagingTemplate messagingTemplate;

    public CollaborationWsController(CollaborationService collaborationService, SimpMessagingTemplate messagingTemplate) {
        this.collaborationService = collaborationService;
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
        log.info("ws.event.in eventId={} type={} sessionId={} actor={} payloadKeys={}",
                event.eventId(),
                event.type(),
                event.sessionId(),
                actor,
                event.payload() == null ? 0 : event.payload().size());

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

        collaborationService.requireMember(event.sessionId(), actor);

        WsEventEnvelope applied = collaborationService.applyAnnotationEvent(event, actor);
        if (applied != null) {
            messagingTemplate.convertAndSend("/topic/sessions/" + event.sessionId(), applied);
            log.info("ws.event.out eventId={} type={} sessionId={} actor={} version={} destination={}",
                    applied.eventId(),
                    applied.type(),
                    applied.sessionId(),
                    applied.actorId(),
                    applied.version(),
                    "/topic/sessions/" + applied.sessionId());
            emitSessionUpdated(event.sessionId(), actor, "annotation");
        } else {
            log.info("ws.event.skipped reason=duplicate eventId={} type={} sessionId={} actor={}",
                    event.eventId(),
                    event.type(),
                    event.sessionId(),
                    actor);
        }
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
}


