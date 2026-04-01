package annotation_server.annotation_service.controller;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.service.CollaborationService;
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

    private final CollaborationService collaborationService;
    private final SimpMessagingTemplate messagingTemplate;

    public CollaborationWsController(CollaborationService collaborationService, SimpMessagingTemplate messagingTemplate) {
        this.collaborationService = collaborationService;
        this.messagingTemplate = messagingTemplate;
    }

    @MessageMapping("/collab.event")
    public void onEvent(@Payload WsEventEnvelope event, Principal principal) {
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            throw new AccessDeniedException("Missing principal");
        }
        if (event == null || event.sessionId() == null || event.sessionId().isBlank() || event.type() == null) {
            throw new IllegalArgumentException("Invalid event envelope");
        }
        String actor = principal.getName().toLowerCase();

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
            return;
        }

        collaborationService.requireMember(event.sessionId(), actor);

        WsEventEnvelope applied = collaborationService.applyAnnotationEvent(event, actor);
        if (applied != null) {
            messagingTemplate.convertAndSend("/topic/sessions/" + event.sessionId(), applied);
        }
    }
}


