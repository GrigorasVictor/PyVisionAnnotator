package annotation_server.annotation_service.entity;

import lombok.Data;

@Data
public class Rectangle {
    private String id;
    private String label;
    private Point point;
    private float width;
    private float height;
    private String color;
}
