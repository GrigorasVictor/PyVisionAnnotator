package annotation_server.annotation_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.Set;

@Data
@AllArgsConstructor
public class PresenceEvent {
    private String type;
    private String userId;
    private Set<String> onlineUsers;
}

