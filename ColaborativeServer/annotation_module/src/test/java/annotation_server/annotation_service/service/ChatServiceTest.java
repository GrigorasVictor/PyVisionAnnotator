package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class ChatServiceTest {

    private CollaborationService collaborationService;

    @BeforeEach
    void setUp() {
        collaborationService = new CollaborationService(
                new TempImageStore(),
                new EventDedupStore(Duration.ofMinutes(10)),
                Duration.ofMinutes(5),
                2_000_000
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
        assertEquals(2, applied.version());
    }

    @Test
    void applyMaskAnnotationKeepsPayloadOpaqueAndUnchanged() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_001", "cam_1", "Session 1");
        collaborationService.markUser("sess_001", "ana@gmail.com", "EDITOR", "ONLINE");

        Map<String, Object> payload = Map.of(
                "id", "ann_mask_001",
                "type", "mask",
                "label", "road",
                "mask", Map.of(
                        "encoding", "json+zlib+base64",
                        "data", "eJyrVkrLz1eyUkpKLFKqBQAQ9wQm",
                        "count", 5821
                )
        );

        WsEventEnvelope incoming = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CREATE.value(),
                "sess_001",
                "proj_alpha",
                "img_001",
                "cam_1",
                null,
                0,
                Instant.now(),
                payload
        );

        WsEventEnvelope applied = collaborationService.applyAnnotationEvent(incoming, "ana@gmail.com");
        assertNotNull(applied);
        assertEquals("mask", applied.payload().get("type"));
        assertEquals("eJyrVkrLz1eyUkpKLFKqBQAQ9wQm", ((Map<?, ?>) applied.payload().get("mask")).get("data"));
        assertEquals(payload, collaborationService.snapshot("sess_001").annotations().get(0));
    }

    @Test
    void maskAnnotationRequiresEncodingAndData() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_001", "cam_1", "Session 1");
        collaborationService.markUser("sess_001", "ana@gmail.com", "EDITOR", "ONLINE");

        WsEventEnvelope missingData = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CREATE.value(),
                "sess_001",
                "proj_alpha",
                "img_001",
                "cam_1",
                null,
                0,
                Instant.now(),
                Map.of(
                        "id", "ann_mask_001",
                        "type", "mask",
                        "mask", Map.of("encoding", "json+zlib+base64")
                )
        );

        assertThrows(IllegalArgumentException.class, () -> collaborationService.applyAnnotationEvent(missingData, "ana@gmail.com"));
    }

    @Test
    void applyRleMaskAnnotationIsAcceptedAndStored() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_001", "cam_1", "Session 1");
        collaborationService.markUser("sess_001", "ana@gmail.com", "EDITOR", "ONLINE");

        Map<String, Object> payload = Map.of(
                "id", "ann_mask_002",
                "type", "mask",
                "label", "person",
                "mask", Map.of(
                        "format", "rle",
                        "size", java.util.List.of(1080, 1920),
                        "counts", "eNq7VjA0M..."
                )
        );

        WsEventEnvelope incoming = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CREATE.value(),
                "sess_001",
                "proj_alpha",
                "img_001",
                "cam_1",
                null,
                0,
                Instant.now(),
                payload
        );

        WsEventEnvelope applied = collaborationService.applyAnnotationEvent(incoming, "ana@gmail.com");
        assertNotNull(applied);
        Map<?, ?> mask = (Map<?, ?>) applied.payload().get("mask");
        assertEquals("rle", mask.get("format"));
        assertEquals("eNq7VjA0M...", mask.get("counts"));
        assertEquals(payload, collaborationService.snapshot("sess_001").annotations().get(0));
    }

    @Test
    void applyFlatLegacyMaskAnnotationIsAcceptedAndStored() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_001", "cam_1", "Session 1");
        collaborationService.markUser("sess_001", "ana@gmail.com", "EDITOR", "ONLINE");

        Map<String, Object> payload = Map.of(
                "id", "ann_mask_flat_001",
                "type", "mask",
                "label", "person",
                "mask_encoding", "bitset_v1",
                "mask_data", "BASE64_ZLIB_DATA",
                "mask_origin", java.util.List.of(100, 200),
                "mask_size", java.util.List.of(320, 180)
        );

        WsEventEnvelope incoming = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CREATE.value(),
                "sess_001",
                "proj_alpha",
                "img_001",
                "cam_1",
                null,
                0,
                Instant.now(),
                payload
        );

        WsEventEnvelope applied = collaborationService.applyAnnotationEvent(incoming, "ana@gmail.com");
        assertNotNull(applied);
        assertEquals("bitset_v1", applied.payload().get("mask_encoding"));
        assertEquals("BASE64_ZLIB_DATA", applied.payload().get("mask_data"));
        assertEquals(payload, collaborationService.snapshot("sess_001").annotations().get(0));
    }

    @Test
    void applyFlatRleMaskAnnotationWithoutExplicitFormatIsAccepted() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_001", "cam_1", "Session 1");
        collaborationService.markUser("sess_001", "ana@gmail.com", "EDITOR", "ONLINE");

        Map<String, Object> payload = Map.of(
                "id", "ann_mask_flat_002",
                "type", "mask",
                "label", "road",
                "mask_size", java.util.List.of(1080, 1920),
                "mask_counts", "eNq7VjA0M..."
        );

        WsEventEnvelope incoming = new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CREATE.value(),
                "sess_001",
                "proj_alpha",
                "img_001",
                "cam_1",
                null,
                0,
                Instant.now(),
                payload
        );

        WsEventEnvelope applied = collaborationService.applyAnnotationEvent(incoming, "ana@gmail.com");
        assertNotNull(applied);
        assertEquals("eNq7VjA0M...", applied.payload().get("mask_counts"));
        assertEquals(payload, collaborationService.snapshot("sess_001").annotations().get(0));
    }
}
