package annotation_server.annotation_service.dto;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.Instant;
import java.util.Map;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record WsEventEnvelope(
        String eventId,
        String type,
        String sessionId,
        String projectId,
        String imageId,
        String cameraId,
        String actorId,
        long version,
        Instant timestamp,
        Map<String, Object> payload
) {
}

