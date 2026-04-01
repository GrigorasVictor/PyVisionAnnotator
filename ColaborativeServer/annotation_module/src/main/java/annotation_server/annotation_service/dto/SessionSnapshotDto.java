package annotation_server.annotation_service.dto;

import java.util.List;
import java.util.Map;

public record SessionSnapshotDto(
        String sessionId,
        String projectId,
        String imageId,
        String cameraId,
        String name,
        List<SessionUserDto> users,
        List<Map<String, Object>> annotations,
        ImageMetaDto imageMeta,
        long version
) {
}

