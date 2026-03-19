package annotation_server.chat_service.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class RegisterEventMessage {
    private String email;
    private LocalDateTime timestamp;
    private String eventType;
}

