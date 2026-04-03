package annotation_server.annotation_service.dto;

public record CreateSessionRequestDto(
        String projectId,
        String imageId,
        String cameraId,
        String name
) {
}

