package annotation_server.auth_service.controller;

import annotation_server.auth_service.dto.AuthResponse;
import annotation_server.auth_service.dto.LoginRequest;
import annotation_server.auth_service.dto.RegisterRequest;
import annotation_server.auth_service.service.UserService;
import annotation_server.auth_service.utilities.JWTUtils;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
public class AuthenticationController {

    private static final Logger logger = LoggerFactory.getLogger(AuthenticationController.class);

    @Autowired
    private UserService userService;

    @Autowired
    private JWTUtils jwtUtils;

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        try {
            AuthResponse response = userService.login(request);
            return ResponseEntity.status(response.getStatusCode()).body(response);
        } catch (Exception e) {
            logger.error(e.getMessage());
            return ResponseEntity.status(500)
                    .body(new AuthResponse(500, "Internal server error", null, "SERVER_ERROR"));
        }
    }

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        try {
            AuthResponse response = userService.register(request);
            return ResponseEntity.status(response.getStatusCode()).body(response);
        } catch (Exception e) {
            logger.error(e.getMessage());
            return ResponseEntity.status(500)
                    .body(new AuthResponse(500, "Internal server error", null, "SERVER_ERROR"));
        }
    }

    @PostMapping("/logout")
    public ResponseEntity<String> logout(@RequestHeader("Authorization") String token) {
        try {
            String username = jwtUtils.extractUsername(token.replace("Bearer ", ""));
            userService.logout(username);
            return ResponseEntity.ok("Logged out successfully");
        } catch (Exception e) {
            logger.error(e.getMessage());
            return ResponseEntity.status(500).body("Error during logout");
        }
    }

    @GetMapping("/validate")
    public ResponseEntity<Void> validateToken(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestHeader(value = "X-Forwarded-Method", required = false) String forwardedMethod
    ) {
        try {
            logger.info("Validate token called - Method: {}", forwardedMethod);

            if (forwardedMethod != null && forwardedMethod.equalsIgnoreCase("OPTIONS")) {
                logger.info("OPTIONS request, allowing through");
                return ResponseEntity.ok().build();
            }

            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                logger.warn("No valid Authorization header found");
                return ResponseEntity.status(401).build();
            }

            String token = authHeader.substring(7);
            String username = jwtUtils.extractUsername(token);

            if (username == null || jwtUtils.isTokenExpired(token)) {
                logger.warn("Token expired or invalid for user: {}", username);
                return ResponseEntity.status(401).build();
            }

            logger.info("Token validated successfully - User: {}", username);

            return ResponseEntity.ok()
                    .header("X-User-Id", username)
                    .build();
        } catch (Exception e) {
            logger.error("Token validation error: {}", e.getMessage(), e);
            return ResponseEntity.status(401).build();
        }
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<AuthResponse> handleValidationError(MethodArgumentNotValidException exception) {
        String message = exception.getBindingResult()
                .getFieldErrors()
                .stream()
                .findFirst()
                .map(error -> error.getDefaultMessage())
                .orElse("Invalid request payload");

        return ResponseEntity.status(400)
                .body(new AuthResponse(400, message, null, "VALIDATION_ERROR"));
    }
}

