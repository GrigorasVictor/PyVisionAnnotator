package annotation_server.annotation_service.config;

import java.security.Principal;

public record WsPrincipal(String name) implements Principal {
	@Override
	public String getName() {
		return name;
	}
}

