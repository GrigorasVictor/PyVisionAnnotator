package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.AnnotationChunkPayloadDto;
import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class AnnotationChunkAssemblyService {

    private static final Logger log = LoggerFactory.getLogger(AnnotationChunkAssemblyService.class);
    private static final TypeReference<Map<String, Object>> MAP_REF = new TypeReference<>() {
    };

    private final ObjectMapper objectMapper;
    private final Duration chunkTtl;
    private final int maxChunkedPayloadChars;

    private final Map<ChunkKey, PendingChunkState> pendingByChunk = new ConcurrentHashMap<>();

    public AnnotationChunkAssemblyService(ObjectMapper objectMapper,
                                          @Value("${collab.chunk-ttl:PT45S}") Duration chunkTtl,
                                          @Value("${collab.chunk-max-total-chars:3000000}") int maxChunkedPayloadChars) {
        this.objectMapper = objectMapper;
        this.chunkTtl = chunkTtl;
        this.maxChunkedPayloadChars = maxChunkedPayloadChars;
    }

    public WsEventEnvelope acceptChunk(WsEventEnvelope incoming, String actorId) {
        AnnotationChunkPayloadDto chunk = parseChunkPayload(incoming);
        ChunkKey key = new ChunkKey(chunk.chunkId(), chunk.sessionId());

        PendingChunkState state;
        try {
            state = pendingByChunk.compute(key, (k, existing) -> {
                PendingChunkState current = existing;
                Instant now = Instant.now();
                if (current == null || current.isExpired(now, chunkTtl)) {
                    current = new PendingChunkState(
                            chunk.chunkId(),
                            chunk.sessionId(),
                            chunk.originalType(),
                            chunk.total(),
                            chunk.encoding(),
                            actorId,
                            now
                    );
                }
                current.addChunk(chunk, actorId, maxChunkedPayloadChars);
                return current;
            });
        } catch (RuntimeException ex) {
            pendingByChunk.remove(key);
            throw ex;
        }

        if (!state.isComplete()) {
            log.info("annotation.chunk.accepted chunkId={} sessionId={} index={} total={} received={}",
                    chunk.chunkId(), chunk.sessionId(), chunk.index(), chunk.total(),
                    state.receivedCount());
            return null;
        }

        pendingByChunk.remove(key);
        return state.reassemble(objectMapper, maxChunkedPayloadChars);
    }

    @Scheduled(fixedDelayString = "${collab.cleanup-interval-ms:60000}")
    public void cleanupExpired() {
        cleanupExpired(Instant.now());
    }

    void cleanupExpired(Instant now) {
        pendingByChunk.entrySet().removeIf(entry -> {
            boolean expired = entry.getValue().isExpired(now, chunkTtl);
            if (expired) {
                log.info("annotation.chunk.cleaned chunkId={} sessionId={} ttl={}",
                        entry.getValue().chunkId,
                        entry.getValue().sessionId,
                        chunkTtl);
            }
            return expired;
        });
    }

    int pendingCount() {
        return pendingByChunk.size();
    }

    private AnnotationChunkPayloadDto parseChunkPayload(WsEventEnvelope incoming) {
        if (!EventType.ANNOTATION_CHUNK.value().equals(incoming.type())) {
            throw new IllegalArgumentException("Unsupported event type for chunk assembly: " + incoming.type());
        }
        if (incoming.payload() == null) {
            throw new IllegalArgumentException("Chunk payload is required");
        }

        AnnotationChunkPayloadDto chunk = objectMapper.convertValue(incoming.payload(), AnnotationChunkPayloadDto.class);
        String chunkId = requireText(chunk.chunkId(), "payload.chunkId");
        String payloadSessionId = requireText(chunk.sessionId(), "payload.sessionId");
        if (!payloadSessionId.equals(incoming.sessionId())) {
            throw new IllegalArgumentException("payload.sessionId must match envelope.sessionId");
        }
        String originalType = requireText(chunk.originalType(), "payload.originalType");
        if (EventType.ANNOTATION_CHUNK.value().equals(originalType)) {
            throw new IllegalArgumentException("payload.originalType cannot be annotation.chunk");
        }
        int index = chunk.index();
        int total = chunk.total();
        if (index < 0) {
            throw new IllegalArgumentException("payload.index must be >= 0");
        }
        if (total <= 0) {
            throw new IllegalArgumentException("payload.total must be > 0");
        }
        if (index >= total) {
            throw new IllegalArgumentException("payload.index must be < payload.total");
        }
        String encoding = requireText(chunk.encoding(), "payload.encoding").toLowerCase();
        if (!"base64".equals(encoding)) {
            throw new IllegalArgumentException("payload.encoding must be base64");
        }
        String data = requireText(chunk.data(), "payload.data");

        return new AnnotationChunkPayloadDto(chunkId, payloadSessionId, originalType, index, total, encoding, data);
    }

    private String requireText(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(fieldName + " is required");
        }
        return value;
    }

    private static final class ChunkKey {
        private final String chunkId;
        private final String sessionId;

        private ChunkKey(String chunkId, String sessionId) {
            this.chunkId = chunkId;
            this.sessionId = sessionId;
        }

        @Override
        public boolean equals(Object obj) {
            if (this == obj) {
                return true;
            }
            if (!(obj instanceof ChunkKey other)) {
                return false;
            }
            return chunkId.equals(other.chunkId) && sessionId.equals(other.sessionId);
        }

        @Override
        public int hashCode() {
            return 31 * chunkId.hashCode() + sessionId.hashCode();
        }
    }

    private static final class PendingChunkState {
        private final String chunkId;
        private final String sessionId;
        private final String originalType;
        private final int total;
        private final String encoding;
        private final String actorId;
        private final Map<Integer, String> chunksByIndex = new ConcurrentHashMap<>();

        private final Instant createdAt;
        private volatile Instant lastUpdatedAt;
        private volatile int totalChars;

        private PendingChunkState(String chunkId,
                                  String sessionId,
                                  String originalType,
                                  int total,
                                  String encoding,
                                  String actorId,
                                  Instant createdAt) {
            this.chunkId = chunkId;
            this.sessionId = sessionId;
            this.originalType = originalType;
            this.total = total;
            this.encoding = encoding;
            this.actorId = actorId;
            this.createdAt = createdAt;
            this.lastUpdatedAt = createdAt;
        }

        private synchronized void addChunk(AnnotationChunkPayloadDto chunk, String actor, int maxChunkedPayloadChars) {
            if (!sessionId.equals(chunk.sessionId())
                    || !chunkId.equals(chunk.chunkId())
                    || !originalType.equals(chunk.originalType())
                    || !encoding.equals(chunk.encoding())
                    || total != chunk.total()) {
                throw new IllegalArgumentException("Chunk metadata mismatch for chunkId=" + chunk.chunkId());
            }
            if (actorId != null && !actorId.isBlank() && !actorId.equals(actor)) {
                throw new IllegalArgumentException("Chunk sequence must be sent by the same actor");
            }

            String existing = chunksByIndex.get(chunk.index());
            if (existing != null) {
                if (!existing.equals(chunk.data())) {
                    throw new IllegalArgumentException("Duplicate chunk index with different data: " + chunk.index());
                }
                lastUpdatedAt = Instant.now();
                return;
            }

            int updatedChars = totalChars + chunk.data().length();
            if (updatedChars > maxChunkedPayloadChars) {
                throw new IllegalArgumentException("Chunked payload exceeds max size");
            }

            chunksByIndex.put(chunk.index(), chunk.data());
            totalChars = updatedChars;
            lastUpdatedAt = Instant.now();
        }

        private boolean isComplete() {
            return chunksByIndex.size() == total;
        }

        private int receivedCount() {
            return chunksByIndex.size();
        }

        private boolean isExpired(Instant now, Duration ttl) {
            return lastUpdatedAt.plus(ttl).isBefore(now) || createdAt.plus(ttl.multipliedBy(2)).isBefore(now);
        }

        private synchronized WsEventEnvelope reassemble(ObjectMapper objectMapper, int maxChunkedPayloadChars) {
            StringBuilder joined = new StringBuilder(totalChars);
            for (int i = 0; i < total; i++) {
                String chunk = chunksByIndex.get(i);
                if (chunk == null) {
                    throw new IllegalArgumentException("Missing chunk index " + i + " for chunkId=" + chunkId);
                }
                joined.append(chunk);
            }

            if (joined.length() > maxChunkedPayloadChars) {
                throw new IllegalArgumentException("Chunked payload exceeds max size");
            }

            byte[] jsonBytes;
            try {
                jsonBytes = Base64.getDecoder().decode(joined.toString());
            } catch (IllegalArgumentException ex) {
                throw new IllegalArgumentException("Invalid base64 chunk data", ex);
            }

            WsEventEnvelope decoded;
            try {
                decoded = objectMapper.readValue(jsonBytes, WsEventEnvelope.class);
            } catch (IOException ex) {
                throw new IllegalArgumentException("Decoded chunk payload is not a valid WS event JSON", ex);
            }

            if (decoded == null || decoded.type() == null || decoded.sessionId() == null) {
                throw new IllegalArgumentException("Decoded event is missing mandatory fields");
            }
            if (!sessionId.equals(decoded.sessionId())) {
                throw new IllegalArgumentException("Decoded event sessionId mismatch");
            }
            if (!originalType.equals(decoded.type())) {
                throw new IllegalArgumentException("Decoded event type mismatch");
            }

            // Normalized event: actor is set from authenticated principal later in the WS controller.
            Map<String, Object> normalizedPayload = decoded.payload() == null
                    ? Map.of()
                    : objectMapper.convertValue(decoded.payload(), MAP_REF);

            String eventId = decoded.eventId();
            if (eventId == null || eventId.isBlank()) {
                eventId = chunkId;
            }

            return new WsEventEnvelope(
                    eventId,
                    decoded.type(),
                    decoded.sessionId(),
                    decoded.projectId(),
                    decoded.imageId(),
                    decoded.cameraId(),
                    decoded.actorId(),
                    decoded.version(),
                    decoded.timestamp(),
                    normalizedPayload
            );
        }
    }
}



