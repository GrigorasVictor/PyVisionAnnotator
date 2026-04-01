package annotation_server.annotation_service.dto;

public enum EventType {
    SESSION_USER_JOINED("session.user.joined"),
    SESSION_USER_LEFT("session.user.left"),
    ANNOTATION_CREATE("annotation.create"),
    ANNOTATION_UPDATE("annotation.update"),
    ANNOTATION_DELETE("annotation.delete"),
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

