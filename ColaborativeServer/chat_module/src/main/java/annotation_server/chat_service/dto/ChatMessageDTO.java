package annotation_server.chat_service.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ChatMessageDTO {
    private String senderId;
    private String senderDisplayName;
    private String receiverId;
    private String message;
    private LocalDateTime timestamp;
}

