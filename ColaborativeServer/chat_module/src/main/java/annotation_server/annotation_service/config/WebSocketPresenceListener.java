package annotation_server.annotation_service.config;

import annotation_server.annotation_service.dto.PresenceEvent;
import annotation_server.annotation_service.service.ChatService;
import annotation_server.annotation_service.service.PresenceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.messaging.SessionConnectedEvent;
import org.springframework.web.socket.messaging.SessionDisconnectEvent;

import java.security.Principal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component
public class WebSocketPresenceListener {

    private static final Logger log = LoggerFactory.getLogger(WebSocketPresenceListener.class);

    @Autowired
    private PresenceService presenceService;

    @Autowired
    private ChatService chatService;

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @EventListener
    public void onConnected(SessionConnectedEvent event) {
        log.info("SessionConnectedEvent received: headers={} user={}", event.getMessage().getHeaders(), event.getUser());
        Principal principal = event.getUser();
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            log.warn("SessionConnectedEvent with no principal — skipping markOnline");
            return;
        }

        String userId = principal.getName().trim().toLowerCase();
        chatService.ensureUserExists(userId);
        presenceService.markOnline(userId);

        PresenceEvent update = new PresenceEvent("ONLINE", userId, presenceService.getOnlineUsers());
        messagingTemplate.convertAndSend("/topic/presence", update);
        messagingTemplate.convertAndSendToUser(userId, "/queue/presence", update);
    }

    @EventListener
    public void onDisconnected(SessionDisconnectEvent event) {
        log.info("SessionDisconnectEvent received: sessionId={} user={}", event.getSessionId(), event.getUser());
        Principal principal = event.getUser();
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            log.warn("SessionDisconnectEvent with no principal — skipping markOffline");
            return;
        }

        String userId = principal.getName().trim().toLowerCase();
        presenceService.markOffline(userId);

        PresenceEvent update = new PresenceEvent("OFFLINE", userId, presenceService.getOnlineUsers());
        messagingTemplate.convertAndSend("/topic/presence", update);
    }
}
