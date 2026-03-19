package annotation_server.chat_service.entity;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import jakarta.persistence.*;

import java.util.Collection;
import java.util.List;

@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
@Entity
@Table(name = "users")
public class User{

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @JsonProperty("id")
    private Long id;

    @Column(unique = true, nullable = false)
    @JsonProperty("email")
    private String email;

    @Column(nullable = false)
    @JsonProperty("username")
    private String username;
}
