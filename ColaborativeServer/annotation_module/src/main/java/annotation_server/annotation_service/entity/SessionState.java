package annotation_server.annotation_service.entity;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class SessionState {
    private final String sessionId;
    private final String projectId;
    private volatile String imageId;
    private volatile String cameraId;
    private volatile String name;
    private final Map<String, SessionUserState> users = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Object>> annotations = new ConcurrentHashMap<>();
    private final AtomicLong version = new AtomicLong(0);
    private volatile Instant lastEventAt = Instant.now();

    public SessionState(String sessionId, String projectId, String imageId, String cameraId, String name) {
        this.sessionId = sessionId;
        this.projectId = projectId;
        this.imageId = imageId;
        this.cameraId = cameraId;
        this.name = name;
    }

    public String getSessionId() {
        return sessionId;
    }

    public String getProjectId() {
        return projectId;
    }

    public String getImageId() {
        return imageId;
    }

    public String getCameraId() {
        return cameraId;
    }

    public String getName() {
        return name;
    }

    public Map<String, SessionUserState> getUsers() {
        return users;
    }

    public Map<String, Map<String, Object>> getAnnotations() {
        return annotations;
    }

    public long getVersion() {
        return version.get();
    }

    public Instant getLastEventAt() {
        return lastEventAt;
    }

    public void updateImage(String imageId, String cameraId, String name) {
        this.imageId = imageId;
        this.cameraId = cameraId;
        this.name = name;
    }

    public long nextVersion(Instant now) {
        this.lastEventAt = now;
        return version.incrementAndGet();
    }
}

