package annotation_server.annotation_service.config;

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
    private SimpMessagingTemplate messagingTemplate;

    @EventListener
    public void onConnected(SessionConnectedEvent event) {
        log.info("ws.connected sessionId={} user={}",
                event.getMessage().getHeaders().get("simpSessionId"),
                event.getUser() == null ? null : event.getUser().getName());
        Principal principal = event.getUser();
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            log.warn("ws.connected.rejected reason=missing_principal");
            return;
        }

        String userId = principal.getName().trim().toLowerCase();
        presenceService.markOnline(userId);

        PresenceEvent update = new PresenceEvent("ONLINE", userId, presenceService.getOnlineUsers());
        messagingTemplate.convertAndSend("/topic/presence", update);
        messagingTemplate.convertAndSendToUser(userId, "/queue/presence", update);
        log.info("ws.presence.out status=ONLINE userId={} onlineCount={} destinations=/topic/presence,/user/{}/queue/presence",
                userId,
                update.onlineUsers().size(),
                userId);
    }

    @EventListener
    public void onDisconnected(SessionDisconnectEvent event) {
        log.info("ws.disconnected sessionId={} user={}",
                event.getSessionId(),
                event.getUser() == null ? null : event.getUser().getName());
        Principal principal = event.getUser();
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            log.warn("ws.disconnected.rejected reason=missing_principal");
            return;
        }

        String userId = principal.getName().trim().toLowerCase();
        presenceService.markOffline(userId);

        PresenceEvent update = new PresenceEvent("OFFLINE", userId, presenceService.getOnlineUsers());
        messagingTemplate.convertAndSend("/topic/presence", update);
        log.info("ws.presence.out status=OFFLINE userId={} onlineCount={} destination=/topic/presence",
                userId,
                update.onlineUsers().size());
    }
}
