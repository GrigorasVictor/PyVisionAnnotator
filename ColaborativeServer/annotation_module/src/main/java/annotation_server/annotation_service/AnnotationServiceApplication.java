package annotation_server.annotation_service;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class AnnotationServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(AnnotationServiceApplication.class, args);
    }

}
