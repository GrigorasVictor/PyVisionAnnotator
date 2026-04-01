package annotation_server.annotation_service.service;

import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class PresenceService {

    private static final Logger log = LoggerFactory.getLogger(PresenceService.class);

    private final Set<String> onlineUsers = ConcurrentHashMap.newKeySet();

    public void markOnline(String userId) {
        if (userId != null && !userId.isBlank()) {
            onlineUsers.add(userId.trim().toLowerCase());
            log.info("markOnline: {} -> onlineUsers.size={}", userId, onlineUsers.size());
        }
    }

    public void markOffline(String userId) {
        if (userId != null && !userId.isBlank()) {
            onlineUsers.remove(userId.trim().toLowerCase());
            log.info("markOffline: {} -> onlineUsers.size={}", userId, onlineUsers.size());
        }
    }

    public Set<String> getOnlineUsers() {
        log.info("getOnlineUsers called -> returning {} users", onlineUsers.size());
        return Collections.unmodifiableSet(onlineUsers);
    }
}
