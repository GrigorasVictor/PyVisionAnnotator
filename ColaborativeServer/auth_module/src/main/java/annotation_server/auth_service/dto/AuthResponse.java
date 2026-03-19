package annotation_server.auth_service.dto;

import annotation_server.auth_service.entity.User;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class AuthResponse {
    private int statusCode;
    private String message;
    private User user;
    private String token;
    private String error;

    public AuthResponse(int statusCode, String message) {
        this.statusCode = statusCode;
        this.message = message;
    }

    public AuthResponse(int statusCode, String message, String token, User user) {
        this.statusCode = statusCode;
        this.message = message;
        this.token = token;
        this.user = user;
    }

    public AuthResponse(int statusCode, String message, String token, String error) {
        this.statusCode = statusCode;
        this.message = message;
        this.token = token;
        this.error = error;
    }
}

