package annotation_server.annotation_service.entity;

import annotation_server.annotation_service.dto.ImageMetaDto;

public record TempImageData(
        byte[] content,
        String token,
        ImageMetaDto metadata
) {
}

