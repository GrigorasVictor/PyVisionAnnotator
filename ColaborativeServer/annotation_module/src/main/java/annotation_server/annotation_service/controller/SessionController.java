package annotation_server.annotation_service.controller;

import annotation_server.annotation_service.dto.CreateSessionRequestDto;
import annotation_server.annotation_service.dto.CreateSessionResponseDto;
import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.SessionSnapshotDto;
import annotation_server.annotation_service.dto.SessionsResponseDto;
import annotation_server.annotation_service.service.CollaborationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/sessions")
public class SessionController {

    private static final Logger log = LoggerFactory.getLogger(SessionController.class);

    private final CollaborationService collaborationService;
    private final SimpMessagingTemplate messagingTemplate;

    public SessionController(CollaborationService collaborationService,
                             SimpMessagingTemplate messagingTemplate) {
        this.collaborationService = collaborationService;
        this.messagingTemplate = messagingTemplate;
    }

    @GetMapping
    public SessionsResponseDto getSessions() {
        log.info("sessions.get.in");
        return collaborationService.listSessions();
    }

    @PostMapping
    public CreateSessionResponseDto createSession(@RequestBody(required = false) CreateSessionRequestDto request,
                                                  Authentication authentication) {
        String actor = authentication == null ? "" : String.valueOf(authentication.getPrincipal());
        log.info("sessions.create.in actor={} projectId={} imageId={} cameraId={} name={}",
                actor,
                request == null ? null : request.projectId(),
                request == null ? null : request.imageId(),
                request == null ? null : request.cameraId(),
                request == null ? null : request.name());
        CreateSessionResponseDto created = collaborationService.createSession(
                request == null ? null : request.projectId(),
                request == null ? null : request.imageId(),
                request == null ? null : request.cameraId(),
                request == null ? null : request.name(),
                actor
        );

        messagingTemplate.convertAndSend(
                "/topic/sessions",
                collaborationService.buildSessionListEvent(
                        EventType.SESSION_CREATED.value(),
                        created.sessionId(),
                        actor,
                        "created"
                )
        );
        log.info("ws.event.out type={} sessionId={} actor={} destination={}",
                EventType.SESSION_CREATED.value(),
                created.sessionId(),
                actor,
                "/topic/sessions");

        return created;
    }

    @GetMapping("/{sessionId}/snapshot")
    public SessionSnapshotDto getSnapshot(@PathVariable String sessionId, Authentication authentication) {
        String actor = authentication == null ? "" : String.valueOf(authentication.getPrincipal());
        log.info("sessions.snapshot.in sessionId={} actor={}", sessionId, actor);
        collaborationService.ensureMember(sessionId, actor, "EDITOR", "ONLINE");
        collaborationService.requireMember(sessionId, actor);
        return collaborationService.snapshot(sessionId);
    }
}


