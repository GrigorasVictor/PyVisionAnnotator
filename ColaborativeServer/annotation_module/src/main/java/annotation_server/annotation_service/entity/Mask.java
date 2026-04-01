package annotation_server.annotation_service.entity;

import lombok.Data;

import java.util.List;

@Data
public class Mask {
    private String id;
    private String label;
    private String color;
    private List<Point> points;
}
