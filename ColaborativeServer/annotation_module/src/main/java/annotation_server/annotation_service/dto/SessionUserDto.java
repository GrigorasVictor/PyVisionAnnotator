package annotation_server.annotation_service.dto;

import java.time.Instant;

public record SessionUserDto(
        String userId,
        String displayName,
        String status,
        String role,
        Instant joinedAt,
        Instant lastSeenAt
) {
}

