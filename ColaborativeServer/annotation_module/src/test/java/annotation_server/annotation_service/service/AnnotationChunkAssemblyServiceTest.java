package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AnnotationChunkAssemblyServiceTest {

    private final ObjectMapper objectMapper = new ObjectMapper().registerModule(new JavaTimeModule());

    @Test
    void assemblesChunksAndReturnsOriginalEvent() throws Exception {
        AnnotationChunkAssemblyService service = new AnnotationChunkAssemblyService(
                objectMapper,
                Duration.ofSeconds(45),
                100_000
        );

        WsEventEnvelope original = new WsEventEnvelope(
                "evt-1",
                EventType.ANNOTATION_UPDATE.value(),
                "sess_01",
                "proj_alpha",
                "img_1",
                "cam_1",
                "ana@gmail.com",
                0,
                Instant.now(),
                Map.of("id", "ann_mask_001", "type", "mask", "points", java.util.List.of(java.util.List.of(1.0, 2.0)))
        );

        String json = objectMapper.writeValueAsString(original);
        String encoded = Base64.getEncoder().encodeToString(json.getBytes(StandardCharsets.UTF_8));
        int mid = encoded.length() / 2;

        WsEventEnvelope part0 = chunkEvent("chunk-a", "sess_01", EventType.ANNOTATION_UPDATE.value(), 0, 2, encoded.substring(0, mid));
        WsEventEnvelope part1 = chunkEvent("chunk-a", "sess_01", EventType.ANNOTATION_UPDATE.value(), 1, 2, encoded.substring(mid));

        WsEventEnvelope first = service.acceptChunk(part0, "ana@gmail.com");
        WsEventEnvelope completed = service.acceptChunk(part1, "ana@gmail.com");

        assertNull(first);
        assertNotNull(completed);
        assertEquals(EventType.ANNOTATION_UPDATE.value(), completed.type());
        assertEquals("sess_01", completed.sessionId());
        assertEquals("ann_mask_001", String.valueOf(completed.payload().get("id")));
    }

    @Test
    void rejectsOutOfRangeIndex() {
        AnnotationChunkAssemblyService service = new AnnotationChunkAssemblyService(
                objectMapper,
                Duration.ofSeconds(45),
                100_000
        );

        WsEventEnvelope invalid = chunkEvent("chunk-b", "sess_01", EventType.ANNOTATION_UPDATE.value(), 2, 2, "Zm9v");

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                () -> service.acceptChunk(invalid, "ana@gmail.com"));
        assertEquals("payload.index must be < payload.total", ex.getMessage());
    }

    @Test
    void rejectsOversizedChunkedPayload() {
        AnnotationChunkAssemblyService service = new AnnotationChunkAssemblyService(
                objectMapper,
                Duration.ofSeconds(45),
                10
        );

        WsEventEnvelope tooLarge = chunkEvent("chunk-c", "sess_01", EventType.ANNOTATION_UPDATE.value(), 0, 1, "abcdefghijk");

        assertThrows(IllegalArgumentException.class, () -> service.acceptChunk(tooLarge, "ana@gmail.com"));
    }

    @Test
    void cleansUpExpiredPartialChunks() {
        AnnotationChunkAssemblyService service = new AnnotationChunkAssemblyService(
                objectMapper,
                Duration.ofSeconds(30),
                100_000
        );

        WsEventEnvelope part = chunkEvent("chunk-d", "sess_01", EventType.ANNOTATION_UPDATE.value(), 0, 2, "Zm9v");
        assertNull(service.acceptChunk(part, "ana@gmail.com"));
        assertEquals(1, service.pendingCount());

        service.cleanupExpired(Instant.now().plusSeconds(31));
        assertEquals(0, service.pendingCount());
    }

    private WsEventEnvelope chunkEvent(String chunkId,
                                       String sessionId,
                                       String originalType,
                                       int index,
                                       int total,
                                       String data) {
        return new WsEventEnvelope(
                UUID.randomUUID().toString(),
                EventType.ANNOTATION_CHUNK.value(),
                sessionId,
                "proj_alpha",
                "img_1",
                "cam_1",
                null,
                0,
                Instant.now(),
                Map.of(
                        "chunkId", chunkId,
                        "sessionId", sessionId,
                        "originalType", originalType,
                        "index", index,
                        "total", total,
                        "encoding", "base64",
                        "data", data
                )
        );
    }
}

