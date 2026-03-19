package annotation_server.auth_service.service;

import annotation_server.auth_service.dto.AuthResponse;
import annotation_server.auth_service.dto.EventMessage;
import annotation_server.auth_service.dto.LoginRequest;
import annotation_server.auth_service.dto.RegisterRequest;
import annotation_server.auth_service.entity.User;
import annotation_server.auth_service.repo.UserRepository;
import annotation_server.auth_service.utilities.JWTUtils;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private JWTUtils jwtUtils;

    @Mock
    private AuthenticationManager authenticationManager;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private RabbitTemplate rabbitTemplate;

    @InjectMocks
    private UserService userService;

    @Test
    void registerReturnsConflictWhenEmailAlreadyExists() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("user@example.com");
        request.setPassword("secret123");

        when(userRepository.findByEmail("user@example.com")).thenReturn(Optional.of(new User()));

        AuthResponse response = userService.register(request);

        assertEquals(409, response.getStatusCode());
        assertEquals("USER_EXISTS", response.getError());
    }

    @Test
    void registerCreatesUserAndReturnsSafeUser() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("new@example.com");
        request.setPassword("secret123");

        User savedUser = new User();
        savedUser.setId(10L);
        savedUser.setEmail("new@example.com");
        savedUser.setPassword("hashedPassword");

        when(userRepository.findByEmail("new@example.com")).thenReturn(Optional.empty());
        when(passwordEncoder.encode("secret123")).thenReturn("hashedPassword");
        when(userRepository.save(any(User.class))).thenReturn(savedUser);

        AuthResponse response = userService.register(request);

        assertEquals(201, response.getStatusCode());
        assertNotNull(response.getUser());
        assertEquals(10L, response.getUser().getId());
        assertEquals("new@example.com", response.getUser().getEmail());
        assertNull(response.getUser().getPassword());
        verify(rabbitTemplate).convertAndSend(eq("auth.events"), eq("auth.user.register"), any(EventMessage.class));
    }

    @Test
    void loginReturnsTokenWhenCredentialsAreValid() {
        LoginRequest request = new LoginRequest();
        request.setEmail("user@example.com");
        request.setPassword("secret123");

        User user = new User();
        user.setId(1L);
        user.setEmail("user@example.com");
        user.setPassword("hashed");

        when(userRepository.findByEmail("user@example.com")).thenReturn(Optional.of(user));
        when(jwtUtils.generateToken(user)).thenReturn("jwt-token");

        AuthResponse response = userService.login(request);

        verify(authenticationManager).authenticate(new UsernamePasswordAuthenticationToken("user@example.com", "secret123"));
        assertEquals(200, response.getStatusCode());
        assertEquals("jwt-token", response.getToken());
        assertEquals("user@example.com", response.getUser().getEmail());
    }

    @Test
    void loginReturnsUnauthorizedWhenCredentialsAreInvalid() {
        LoginRequest request = new LoginRequest();
        request.setEmail("user@example.com");
        request.setPassword("wrong-password");

        when(authenticationManager.authenticate(any())).thenThrow(new BadCredentialsException("Invalid"));

        AuthResponse response = userService.login(request);

        assertEquals(401, response.getStatusCode());
        assertEquals("INVALID_CREDENTIALS", response.getError());
    }
}


