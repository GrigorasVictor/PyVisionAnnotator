package annotation_server.annotation_service;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.support.TestJwtFactory;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.messaging.converter.MappingJackson2MessageConverter;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;

import java.lang.reflect.Type;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AnnotationSyncIT {

    @LocalServerPort
    private int port;

    private StompSession sessionA;
    private StompSession sessionB;

    @AfterEach
    void tearDown() {
        if (sessionA != null && sessionA.isConnected()) {
            sessionA.disconnect();
        }
        if (sessionB != null && sessionB.isConnected()) {
            sessionB.disconnect();
        }
    }

    @Test
    void annotationCreateIsBroadcastToAnotherClient() throws Exception {
        WebSocketStompClient client = new WebSocketStompClient(new StandardWebSocketClient());
        client.setMessageConverter(new MappingJackson2MessageConverter());

        sessionA = connect(client, "ana@gmail.com");
        sessionB = connect(client, "alex@gmail.com");

        BlockingQueue<WsEventEnvelope> eventsB = new LinkedBlockingQueue<>();
        sessionB.subscribe("/topic/sessions/sess_ws_01", new EnvelopeHandler(eventsB));

        sessionA.send("/app/collab.event", event(EventType.SESSION_USER_JOINED.value(), "sess_ws_01", Map.of()));
        sessionB.send("/app/collab.event", event(EventType.SESSION_USER_JOINED.value(), "sess_ws_01", Map.of()));

        sessionA.send("/app/collab.event", event(
                EventType.ANNOTATION_CREATE.value(),
                "sess_ws_01",
                Map.of("id", "ann_rect_001", "type", "rect", "label", "car", "x", 10.0, "y", 11.0, "w", 12.0, "h", 13.0)
        ));

        WsEventEnvelope received = eventsB.poll(5, TimeUnit.SECONDS);
        while (received != null && !EventType.ANNOTATION_CREATE.value().equals(received.type())) {
            received = eventsB.poll(5, TimeUnit.SECONDS);
        }

        assertNotNull(received);
        assertEquals("sess_ws_01", received.sessionId());
        assertEquals("ann_rect_001", String.valueOf(received.payload().get("id")));
    }

    private StompSession connect(WebSocketStompClient client, String userId) throws Exception {
        String wsUrl = "ws://localhost:" + port + "/ws";
        StompHeaders headers = new StompHeaders();
        headers.add("Authorization", TestJwtFactory.bearerFor(userId));
        return client.connectAsync(wsUrl, new org.springframework.web.socket.WebSocketHttpHeaders(), headers,
                new StompSessionHandlerAdapter() {
                }).get(5, TimeUnit.SECONDS);
    }

    private WsEventEnvelope event(String type, String sessionId, Map<String, Object> payload) {
        return new WsEventEnvelope(
                UUID.randomUUID().toString(),
                type,
                sessionId,
                "proj_alpha",
                "img_0001",
                "cam_01",
                null,
                0,
                Instant.now(),
                payload
        );
    }

    private static class EnvelopeHandler implements StompFrameHandler {

        private final BlockingQueue<WsEventEnvelope> queue;

        private EnvelopeHandler(BlockingQueue<WsEventEnvelope> queue) {
            this.queue = queue;
        }

        @Override
        public Type getPayloadType(StompHeaders headers) {
            return WsEventEnvelope.class;
        }

        @Override
        public void handleFrame(StompHeaders headers, Object payload) {
            if (payload instanceof WsEventEnvelope envelope) {
                queue.offer(envelope);
            }
        }
    }
}



