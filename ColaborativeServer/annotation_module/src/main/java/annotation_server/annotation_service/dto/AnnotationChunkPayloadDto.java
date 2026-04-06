package annotation_server.annotation_service.dto;

public record AnnotationChunkPayloadDto(
        String chunkId,
        String sessionId,
        String originalType,
        int index,
        int total,
        String encoding,
        String data
) {
}

