package annotation_server.chat_service.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Autowired
    private GatewayAuthHeaderFilter gatewayAuthHeaderFilter;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity httpSecurity) throws Exception {
        httpSecurity
                .cors(AbstractHttpConfigurer::disable)
                .csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(request -> request
                        .requestMatchers("/actuator/**").permitAll()
                        .requestMatchers("/chat/admin/**").hasAuthority("ROLE_ADMIN")
                        .requestMatchers("/chat/**", "/notifications/**").hasAnyAuthority("ROLE_ADMIN", "ROLE_CLIENT", "ROLE_USER")
                        .requestMatchers("/monitor/**", "/ws/**").hasAnyAuthority("ROLE_ADMIN", "ROLE_CLIENT", "ROLE_USER")
                        .anyRequest().authenticated()
                )
                .sessionManagement(manager -> manager.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .addFilterBefore(gatewayAuthHeaderFilter, UsernamePasswordAuthenticationFilter.class);

        return httpSecurity.build();
    }

}
