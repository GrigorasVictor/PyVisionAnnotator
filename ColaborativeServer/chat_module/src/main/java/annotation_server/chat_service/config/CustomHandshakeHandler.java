package annotation_server.chat_service.config;

import org.springframework.http.server.ServerHttpRequest;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.support.DefaultHandshakeHandler;

import java.net.URI;
import java.security.Principal;
import java.util.List;
import java.util.Map;

public class CustomHandshakeHandler extends DefaultHandshakeHandler {

    @Override
    protected Principal determineUser(ServerHttpRequest request, WebSocketHandler wsHandler, Map<String, Object> attributes) {
        List<String> header = request.getHeaders().get("X-User-Id");
        String user = null;
        if (header != null && !header.isEmpty()) {
            user = header.get(0);
        }
        // Fallback: try query parameter ?user=...
        if (user == null || user.isBlank()) {
            URI uri = request.getURI();
            if (uri != null && uri.getQuery() != null) {
                String[] parts = uri.getQuery().split("&");
                for (String p : parts) {
                    if (p.startsWith("user=") || p.startsWith("userId=") || p.startsWith("X-User-Id=")) {
                        String[] kv = p.split("=", 2);
                        if (kv.length == 2) { user = kv[1]; break; }
                    }
                }
            }
        }

        if (user == null || user.isBlank()) {
            return super.determineUser(request, wsHandler, attributes);
        }

        final String username = user.trim().toLowerCase();
        return new Principal() {
            @Override
            public String getName() {
                return username;
            }
        };
    }
}

