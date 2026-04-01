package annotation_server.annotation_service.dto;

import java.time.Instant;
import java.util.List;

public record SessionItemDto(
        String sessionId,
        String projectId,
        String imageId,
        String cameraId,
        String name,
        List<SessionUserDto> users,
        int onlineCount,
        Instant lastEventAt,
        long version
) {
}

