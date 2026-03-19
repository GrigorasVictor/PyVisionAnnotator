package annotation_server.auth_service.service;

import annotation_server.auth_service.dto.AuthResponse;
import annotation_server.auth_service.dto.EventMessage;
import annotation_server.auth_service.dto.LoginRequest;
import annotation_server.auth_service.dto.RegisterRequest;
import annotation_server.auth_service.entity.User;
import annotation_server.auth_service.repo.UserRepository;
import annotation_server.auth_service.utilities.JWTUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class UserService extends AbstractService<User, UserRepository> {
    private static final Logger logger = LoggerFactory.getLogger(UserService.class);

    @Autowired
    private UserRepository userRepository;
    @Autowired
    private JWTUtils jwtUtils;
    @Autowired
    private AuthenticationManager authenticationManager;
    @Autowired
    private PasswordEncoder passwordEncoder;
    @Autowired
    private RabbitTemplate rabbitTemplate;

    public AuthResponse register(RegisterRequest request) {
        try {
            if (userRepository.findByEmail(request.getEmail()).isPresent()) {
                return new AuthResponse(409, "User already exists", null, "USER_EXISTS");
            }

            User user = new User();
            user.setEmail(request.getEmail());
            user.setPassword(passwordEncoder.encode(request.getPassword()));

            User persisted = userRepository.save(user);
            publishRegisterEvent(persisted);

            return new AuthResponse(201, "User registered successfully", null, toSafeUser(persisted));
        } catch (Exception e) {
            logger.error("Registration failed for email: {}", request.getEmail(), e);
            return new AuthResponse(500, "Error during registration", null, "REGISTRATION_ERROR");
        }
    }

    public AuthResponse login(LoginRequest request) {
        try {
            authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword())
            );

            User user = userRepository.findByEmail(request.getEmail())
                    .orElseThrow(() -> new BadCredentialsException("Invalid email or password"));

            String token = jwtUtils.generateToken(user);
            return new AuthResponse(200, "Login successful", token, toSafeUser(user));
        } catch (BadCredentialsException e) {
            return new AuthResponse(401, "Invalid email or password", null, "INVALID_CREDENTIALS");
        } catch (Exception e) {
            logger.error("Login failed for email: {}", request.getEmail(), e);
            return new AuthResponse(500, "Error during login", null, "LOGIN_ERROR");
        }
    }

    public void logout(String username) {
        logger.info("Logout request received for user: {}", username);
    }

    private void publishRegisterEvent(User user) {
        try {
            EventMessage message = EventMessage.builder()
                    .username(user.getUsername())
                    .password("")
                    .timestamp(java.time.LocalDateTime.now())
                    .eventType("register")
                    .build();

            rabbitTemplate.convertAndSend("auth.events", "auth.user.register", message);
        } catch (Exception e) {
            logger.warn("User created but register event was not published for {}", user.getUsername(), e);
        }
    }

    private User toSafeUser(User user) {
        User safeUser = new User();
        safeUser.setId(user.getId());
        safeUser.setEmail(user.getEmail());
        return safeUser;
    }
}