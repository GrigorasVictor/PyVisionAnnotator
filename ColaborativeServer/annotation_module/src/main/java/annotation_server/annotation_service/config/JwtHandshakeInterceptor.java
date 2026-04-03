package annotation_server.annotation_service.config;

import annotation_server.annotation_service.service.JwtService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import java.util.Map;

@Component
public class JwtHandshakeInterceptor implements HandshakeInterceptor {

    private static final Logger log = LoggerFactory.getLogger(JwtHandshakeInterceptor.class);

    static final String ATTR_USER_ID = "wsUserId";

    private final JwtService jwtService;

    public JwtHandshakeInterceptor(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response, WebSocketHandler wsHandler,
                                   Map<String, Object> attributes) {
        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        String token = null;

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            token = authHeader.substring(7);
        } else if (request.getURI() != null && request.getURI().getQuery() != null) {
            for (String pair : request.getURI().getQuery().split("&")) {
                String[] kv = pair.split("=", 2);
                if (kv.length == 2 && "token".equals(kv[0])) {
                    token = kv[1];
                    break;
                }
            }
        }

        if (token == null || token.isBlank()) {
            log.warn("ws.handshake.rejected reason=missing_token uri={}", request.getURI());
            response.setStatusCode(HttpStatus.UNAUTHORIZED);
            return false;
        }

        try {
            String userId = jwtService.extractUser(token);
            attributes.put(ATTR_USER_ID, userId);
            log.info("ws.handshake.accepted userId={} uri={}", userId, request.getURI());
            return true;
        } catch (Exception ex) {
            log.warn("ws.handshake.rejected reason=invalid_token uri={} error={}", request.getURI(), ex.getMessage());
            response.setStatusCode(HttpStatus.UNAUTHORIZED);
            return false;
        }
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response, WebSocketHandler wsHandler,
                               Exception exception) {
    }
}

