package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.ImageMetaDto;
import annotation_server.annotation_service.entity.TempImageData;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class TempImageStore {

    private final Map<String, TempImageData> imageMetaById = new ConcurrentHashMap<>();

    public void put(String imageId, TempImageData imageData) {
        imageMetaById.put(imageId, imageData);
    }

    public Optional<TempImageData> get(String imageId) {
        return Optional.ofNullable(imageMetaById.get(imageId));
    }

    public Optional<ImageMetaDto> getMeta(String imageId) {
        return Optional.ofNullable(imageMetaById.get(imageId)).map(TempImageData::metadata);
    }

    @Scheduled(fixedDelayString = "${collab.cleanup-interval-ms:60000}")
    public void cleanupExpired() {
        Instant now = Instant.now();
        imageMetaById.entrySet().removeIf(entry -> entry.getValue().metadata().expiresAt().isBefore(now));
    }
}

