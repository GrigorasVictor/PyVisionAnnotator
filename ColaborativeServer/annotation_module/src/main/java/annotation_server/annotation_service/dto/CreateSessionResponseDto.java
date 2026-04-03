package annotation_server.annotation_service.dto;

public record CreateSessionResponseDto(
        String sessionId,
        String projectId,
        String imageId,
        String cameraId,
        String name
) {
}

