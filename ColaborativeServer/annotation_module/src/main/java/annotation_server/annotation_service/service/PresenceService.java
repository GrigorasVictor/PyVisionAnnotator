package annotation_server.annotation_service.service;

import org.springframework.stereotype.Service;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class PresenceService {

    private final Set<String> onlineUsers = ConcurrentHashMap.newKeySet();

    public void markOnline(String userId) {
        onlineUsers.add(userId);
    }

    public void markOffline(String userId) {
        onlineUsers.remove(userId);
    }

    public Set<String> getOnlineUsers() {
        return Set.copyOf(onlineUsers);
    }
}

