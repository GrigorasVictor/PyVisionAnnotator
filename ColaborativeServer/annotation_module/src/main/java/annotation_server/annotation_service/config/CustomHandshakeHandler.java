package annotation_server.annotation_service.config;

import org.springframework.http.server.ServerHttpRequest;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.support.DefaultHandshakeHandler;

import java.security.Principal;
import java.util.Map;

public class CustomHandshakeHandler extends DefaultHandshakeHandler {

    @Override
    protected Principal determineUser(ServerHttpRequest request, WebSocketHandler wsHandler, Map<String, Object> attributes) {
        Object user = attributes.get(JwtHandshakeInterceptor.ATTR_USER_ID);
        if (!(user instanceof String userId) || userId.isBlank()) {
            return super.determineUser(request, wsHandler, attributes);
        }
        return new WsPrincipal(userId.trim().toLowerCase());
    }
}

