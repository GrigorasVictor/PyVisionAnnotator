package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class ChatServiceTest {

    private CollaborationService collaborationService;

    @BeforeEach
    void setUp() {
        collaborationService = new CollaborationService(
                new TempImageStore(),
                new EventDedupStore(Duration.ofMinutes(10)),
                Duration.ofMinutes(5)
        );
    }

    @Test
    void listSessionsContainsCameraAndUsers() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_001", "cam_1", "Session 1");
        collaborationService.markUser("sess_001", "ana@gmail.com", "EDITOR", "ONLINE");

        var response = collaborationService.listSessions();
        assertEquals(1, response.total());
        assertEquals("cam_1", response.items().get(0).cameraId());
        assertEquals(1, response.items().get(0).users().size());
    }

    @Test
    void applyAnnotationEventIncrementsVersion() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_001", "cam_1", "Session 1");
        collaborationService.markUser("sess_001", "ana@gmail.com", "EDITOR", "ONLINE");

        WsEventEnvelope incoming = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CREATE.value(),
                "sess_001",
                "proj_alpha",
                "img_001",
                "cam_1",
                "ana@gmail.com",
                0,
                null,
                Map.of("id", "ann_1", "type", "rect")
        );

        WsEventEnvelope applied = collaborationService.applyAnnotationEvent(incoming, "ana@gmail.com");
        assertNotNull(applied);
        assertEquals(3, applied.version());
    }
}

