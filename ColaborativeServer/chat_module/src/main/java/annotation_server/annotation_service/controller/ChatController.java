package annotation_server.annotation_service.controller;

import annotation_server.annotation_service.dto.ChatMessageDTO;
import annotation_server.annotation_service.dto.PresenceEvent;
import annotation_server.annotation_service.service.ChatService;
import annotation_server.annotation_service.service.PresenceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.messaging.simp.annotation.SendToUser;
import org.springframework.stereotype.Controller;

import java.security.Principal;
import java.util.List;

@Controller
public class ChatController {

	@Autowired
	private ChatService chatService;

	@Autowired
	private PresenceService presenceService;

	@Autowired
	private SimpMessagingTemplate messagingTemplate;

	@MessageMapping("/chat.send")
	public void sendPrivateMessage(@Payload ChatMessageDTO inbound, Principal principal) {
		String currentUser = requireCurrentUser(principal);
		chatService.sendPrivateMessage(currentUser, inbound.getReceiverId(), inbound.getMessage());
	}

	@MessageMapping("/chat.history")
	public void getConversationHistory(@Payload ChatMessageDTO request, Principal principal) {
		String currentUser = requireCurrentUser(principal);
		List<ChatMessageDTO> response = chatService.getConversation(currentUser, request.getReceiverId());
		messagingTemplate.convertAndSendToUser(currentUser, "/queue/history", response);
	}

	@MessageMapping("/chat.presence")
	public void getPresenceSnapshot(Principal principal) {
		String currentUser = requireCurrentUser(principal);
		PresenceEvent snapshot = new PresenceEvent("SNAPSHOT", currentUser, presenceService.getOnlineUsers());
		messagingTemplate.convertAndSendToUser(currentUser, "/queue/presence", snapshot);
	}

	@org.springframework.messaging.handler.annotation.MessageExceptionHandler
	@SendToUser("/queue/errors")
	public String handleWebSocketError(Exception exception) {
		return exception.getMessage();
	}

	private String requireCurrentUser(Principal principal) {
		if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
			throw new IllegalArgumentException("Unauthenticated websocket session");
		}
		return principal.getName().trim().toLowerCase();
	}
}
