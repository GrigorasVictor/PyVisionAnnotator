package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.ChatMessageDTO;
import annotation_server.annotation_service.entity.User;
import annotation_server.annotation_service.repo.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;

@Slf4j
@Service
public class ChatService {

    private static final int MAX_MESSAGES_PER_CONVERSATION = 200;

    private final Map<String, Deque<ChatMessageDTO>> conversations = new ConcurrentHashMap<>();

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @Autowired
    private UserRepository userRepository;

    public ChatMessageDTO sendPrivateMessage(String senderId, String receiverId, String text) {
        if (senderId == null || senderId.isBlank() || receiverId == null || receiverId.isBlank()) {
            throw new IllegalArgumentException("Sender and receiver are required");
        }
        if (senderId.equalsIgnoreCase(receiverId)) {
            throw new IllegalArgumentException("Direct self chat is not supported");
        }
        if (text == null || text.isBlank()) {
            throw new IllegalArgumentException("Message content is empty");
        }

        String normalizedSender = senderId.trim().toLowerCase();
        String normalizedReceiver = receiverId.trim().toLowerCase();

        if (userRepository.findByEmail(normalizedReceiver).isEmpty()) {
            throw new IllegalArgumentException("Receiver does not exist");
        }

        ChatMessageDTO message = new ChatMessageDTO();
        message.setSenderId(normalizedSender);
        message.setSenderDisplayName(resolveSenderDisplayName(normalizedSender));
        message.setReceiverId(normalizedReceiver);
        message.setMessage(text.trim());
        message.setTimestamp(LocalDateTime.now());

        String key = conversationKey(normalizedSender, normalizedReceiver);
        Deque<ChatMessageDTO> history = conversations.computeIfAbsent(key, ignored -> new ConcurrentLinkedDeque<>());
        history.addLast(message);

        while (history.size() > MAX_MESSAGES_PER_CONVERSATION) {
            history.pollFirst();
        }

        messagingTemplate.convertAndSendToUser(normalizedSender, "/queue/private", message);
        messagingTemplate.convertAndSendToUser(normalizedReceiver, "/queue/private", message);
        return message;
    }

    public List<ChatMessageDTO> getConversation(String requesterId, String otherUserId) {
        if (requesterId == null || requesterId.isBlank() || otherUserId == null || otherUserId.isBlank()) {
            throw new IllegalArgumentException("Requester and peer are required");
        }

        String normalizedRequester = requesterId.trim().toLowerCase();
        String normalizedOther = otherUserId.trim().toLowerCase();

        String key = conversationKey(normalizedRequester, normalizedOther);
        Deque<ChatMessageDTO> history = conversations.get(key);
        if (history == null) {
            return Collections.emptyList();
        }

        return new ArrayList<>(history);
    }

    public String conversationKey(String firstUserId, String secondUserId) {
        String a = firstUserId.trim().toLowerCase();
        String b = secondUserId.trim().toLowerCase();
        return a.compareTo(b) <= 0 ? a + "::" + b : b + "::" + a;
    }

    private String resolveSenderDisplayName(String senderEmail) {
        return userRepository.findByEmail(senderEmail)
                .map(User::getUsername)
                .filter(username -> username != null && !username.isBlank())
                .orElseGet(() -> deriveUsername(senderEmail));
    }

    private String deriveUsername(String email) {
        int separator = email.indexOf('@');
        if (separator <= 0) {
            return email;
        }
        return email.substring(0, separator);
    }

}

