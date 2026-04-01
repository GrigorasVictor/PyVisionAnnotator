package annotation_server.annotation_service.entity;

import java.time.Instant;

public class SessionUserState {
    private final String userId;
    private final String displayName;
    private final String role;
    private volatile String status;
    private final Instant joinedAt;
    private volatile Instant lastSeenAt;

    public SessionUserState(String userId, String displayName, String role, String status, Instant joinedAt, Instant lastSeenAt) {
        this.userId = userId;
        this.displayName = displayName;
        this.role = role;
        this.status = status;
        this.joinedAt = joinedAt;
        this.lastSeenAt = lastSeenAt;
    }

    public String getUserId() {
        return userId;
    }

    public String getDisplayName() {
        return displayName;
    }

    public String getRole() {
        return role;
    }

    public String getStatus() {
        return status;
    }

    public Instant getJoinedAt() {
        return joinedAt;
    }

    public Instant getLastSeenAt() {
        return lastSeenAt;
    }

    public void mark(String status, Instant at) {
        this.status = status;
        this.lastSeenAt = at;
    }
}

