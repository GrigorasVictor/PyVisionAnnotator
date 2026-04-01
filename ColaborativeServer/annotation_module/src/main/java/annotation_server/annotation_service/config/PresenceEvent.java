package annotation_server.annotation_service.config;

import java.util.Set;

public record PresenceEvent(String status, String userId, Set<String> onlineUsers) {
}

