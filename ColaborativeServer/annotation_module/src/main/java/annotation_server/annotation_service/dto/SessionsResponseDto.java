package annotation_server.annotation_service.dto;

import java.util.List;

public record SessionsResponseDto(List<SessionItemDto> items, int total) {
}

