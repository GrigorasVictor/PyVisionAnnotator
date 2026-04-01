package annotation_server.annotation_service.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class EventDedupStore {

    private final Duration ttl;
    private final Map<String, Instant> processedEventIds = new ConcurrentHashMap<>();

    public EventDedupStore(@Value("${collab.event-dedup-ttl:PT10M}") Duration ttl) {
        this.ttl = ttl;
    }

    public boolean isDuplicate(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return false;
        }
        Instant now = Instant.now();
        Instant existing = processedEventIds.putIfAbsent(eventId, now);
        if (existing == null) {
            return false;
        }
        if (existing.plus(ttl).isBefore(now)) {
            processedEventIds.put(eventId, now);
            return false;
        }
        return true;
    }

    @Scheduled(fixedDelayString = "${collab.cleanup-interval-ms:60000}")
    public void cleanupExpired() {
        Instant threshold = Instant.now().minus(ttl);
        processedEventIds.entrySet().removeIf(entry -> entry.getValue().isBefore(threshold));
    }
}

