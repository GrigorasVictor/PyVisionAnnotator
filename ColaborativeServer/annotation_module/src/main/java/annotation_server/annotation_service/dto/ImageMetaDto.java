package annotation_server.annotation_service.dto;

import java.time.Instant;

public record ImageMetaDto(
        String sessionId,
        String imageId,
        String cameraId,
        String fileName,
        String mimeType,
        long sizeBytes,
        int width,
        int height,
        String checksumSha256,
        String downloadUrl,
        Instant expiresAt
) {
}

