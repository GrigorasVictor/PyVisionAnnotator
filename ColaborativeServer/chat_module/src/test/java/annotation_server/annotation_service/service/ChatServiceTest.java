package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.ChatMessageDTO;
import annotation_server.annotation_service.entity.User;
import annotation_server.annotation_service.repo.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import java.util.List;
import java.util.Optional;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ChatServiceTest {

    @Mock
    private SimpMessagingTemplate messagingTemplate;

    @Mock
    private UserRepository userRepository;

    @Mock
    private PresenceService presenceService;

    @InjectMocks
    private ChatService chatService;

    @Test
    void sendPrivateMessageStoresConversationAndNotifiesBothUsers() {
        User sender = new User();
        sender.setEmail("alice@example.com");
        sender.setUsername("alice");
        when(userRepository.findByEmail("alice@example.com")).thenReturn(Optional.of(sender));

        User receiver = new User();
        receiver.setEmail("bob@example.com");
        when(userRepository.findByEmail("bob@example.com")).thenReturn(Optional.of(receiver));

        ChatMessageDTO message = chatService.sendPrivateMessage("alice@example.com", "bob@example.com", "Salut");

        assertEquals("alice@example.com", message.getSenderId());
        assertEquals("alice", message.getSenderDisplayName());
        assertEquals("bob@example.com", message.getReceiverId());
        assertEquals("Salut", message.getMessage());

        List<ChatMessageDTO> history = chatService.getConversation("alice@example.com", "bob@example.com");
        assertEquals(1, history.size());
        assertEquals("Salut", history.get(0).getMessage());

        verify(messagingTemplate, times(1)).convertAndSendToUser(eq("alice@example.com"), eq("/queue/private"), eq(message));
        verify(messagingTemplate, times(1)).convertAndSendToUser(eq("bob@example.com"), eq("/queue/private"), eq(message));
    }

    @Test
    void sendPrivateMessageFallsBackToEmailUsernameWhenSenderUsernameMissing() {
        User sender = new User();
        sender.setEmail("alice@example.com");
        sender.setUsername("   ");
        when(userRepository.findByEmail("alice@example.com")).thenReturn(Optional.of(sender));

        User receiver = new User();
        receiver.setEmail("bob@example.com");
        when(userRepository.findByEmail("bob@example.com")).thenReturn(Optional.of(receiver));

        ChatMessageDTO message = chatService.sendPrivateMessage("alice@example.com", "bob@example.com", "Salut");

        assertEquals("alice", message.getSenderDisplayName());
    }

    @Test
    void sendPrivateMessageFailsWhenReceiverDoesNotExist() {
        User sender = new User();
        sender.setEmail("alice@example.com");
        sender.setUsername("alice");
        when(userRepository.findByEmail("alice@example.com")).thenReturn(Optional.of(sender));
        when(userRepository.findByEmail("ghost@example.com")).thenReturn(Optional.empty());
        when(presenceService.getOnlineUsers()).thenReturn(Set.of());

        assertThrows(IllegalArgumentException.class,
                () -> chatService.sendPrivateMessage("alice@example.com", "ghost@example.com", "Salut"));
    }
}

