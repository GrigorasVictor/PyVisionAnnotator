package annotation_server.annotation_service.service;

import annotation_server.annotation_service.dto.CreateSessionResponseDto;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;

class CollaborationServiceRoomLifecycleTest {

    @Test
    void cleanupRemovesEmptyInactiveRooms() {
        CollaborationService service = new CollaborationService(new TempImageStore(), new EventDedupStore(Duration.ofMinutes(10)), Duration.ofMinutes(5));
        CreateSessionResponseDto created = service.createSession("proj", "img", "cam", "room", "");

        service.cleanupInactiveSessions(Instant.now().plus(Duration.ofMinutes(6)));

        assertEquals(0, service.listSessions().total());
        // Keep test deterministic by validating global count instead of generated room code.
    }

    @Test
    void cleanupKeepsRoomWhenAtLeastOneUserIsOnline() {
        CollaborationService service = new CollaborationService(new TempImageStore(), new EventDedupStore(Duration.ofMinutes(10)), Duration.ofMinutes(5));
        CreateSessionResponseDto created = service.createSession("proj", "img", "cam", "room", "ana@gmail.com");

        service.cleanupInactiveSessions(Instant.now().plus(Duration.ofMinutes(30)));

        assertEquals(created.sessionId(), service.listSessions().items().get(0).sessionId());
        assertEquals(1, service.listSessions().total());
    }
}

