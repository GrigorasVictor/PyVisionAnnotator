package annotation_server.annotation_service.controller;

import annotation_server.annotation_service.dto.SessionSnapshotDto;
import annotation_server.annotation_service.dto.SessionsResponseDto;
import annotation_server.annotation_service.service.CollaborationService;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/sessions")
public class SessionController {

    private final CollaborationService collaborationService;

    public SessionController(CollaborationService collaborationService) {
        this.collaborationService = collaborationService;
    }

    @GetMapping
    public SessionsResponseDto getSessions() {
        return collaborationService.listSessions();
    }

    @GetMapping("/{sessionId}/snapshot")
    public SessionSnapshotDto getSnapshot(@PathVariable String sessionId, Authentication authentication) {
        collaborationService.requireMember(sessionId, String.valueOf(authentication.getPrincipal()));
        return collaborationService.snapshot(sessionId);
    }
}


