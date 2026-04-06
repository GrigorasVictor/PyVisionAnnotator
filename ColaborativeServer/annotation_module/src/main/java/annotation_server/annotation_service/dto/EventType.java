package annotation_server.annotation_service.dto;

public enum EventType {
    SESSION_CREATED("session.created"),
    SESSION_UPDATED("session.updated"),
    SESSION_USER_JOINED("session.user.joined"),
    SESSION_USER_LEFT("session.user.left"),
    ANNOTATION_CREATE("annotation.create"),
    ANNOTATION_UPDATE("annotation.update"),
    ANNOTATION_DELETE("annotation.delete"),
    ANNOTATION_CHUNK("annotation.chunk"),
    ANNOTATION_CHUNK_ACK("annotation.chunk.ack"),
    ANNOTATION_CHUNK_ERROR("annotation.chunk.error"),
    WS_ERROR("ws.error"),
    IMAGE_AVAILABLE("image.available"),
    SNAPSHOT("snapshot");

    private final String value;

    EventType(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }
}

