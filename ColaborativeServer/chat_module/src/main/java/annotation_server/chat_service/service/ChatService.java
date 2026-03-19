package annotation_server.chat_service.service;


import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class ChatService {

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

}

