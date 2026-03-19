package annotation_server.chat_service.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ChatMessageDTO {
    private Long id;
    private String senderId;
    private String senderUsername;
    private String receiverId;
    private String message;
    private LocalDateTime timestamp;
    private Boolean isFromAdmin;
    private Boolean isRead;
    private Boolean isAutomatedResponse;
}

