package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.RegisterEventMessage;
import annotation_server.annotation_service.entity.User;
import annotation_server.annotation_service.repo.UserRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserSyncListener {

    private static final Logger logger = LoggerFactory.getLogger(UserSyncListener.class);

    @Autowired
    private UserRepository userRepository;
    @Autowired
    private ObjectMapper objectMapper;

    @RabbitListener(queues = "${rabbitmq.queue.user-register:chat.user.register.queue}")
    public void onUserRegistered(String payload) {
        RegisterEventMessage event;
        try {
            event = objectMapper.readValue(payload, RegisterEventMessage.class);
        } catch (Exception e) {
            logger.warn("Failed to parse register event payload: {}", payload, e);
            return;
        }

        if (event == null || event.getEmail() == null || event.getEmail().isBlank()) {
            logger.warn("Received invalid register event payload");
            return;
        }

        String email = event.getEmail().trim().toLowerCase();
        String username = deriveUsername(email);

        User user = userRepository.findByEmail(email).orElseGet(User::new);
        user.setEmail(email);
        user.setUsername(username);
        userRepository.save(user);

        logger.info("User synced into chat module: {}", email);
    }

    private String deriveUsername(String email) {
        int separator = email.indexOf('@');
        if (separator <= 0) {
            return email;
        }
        return email.substring(0, separator);
    }
}

