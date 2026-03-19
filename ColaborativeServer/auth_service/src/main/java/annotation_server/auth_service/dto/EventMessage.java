package annotation_server.auth_service.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class EventMessage {
    private String username;
    private String password;
    private String role;
    private LocalDateTime timestamp;
    private String eventType;
}
