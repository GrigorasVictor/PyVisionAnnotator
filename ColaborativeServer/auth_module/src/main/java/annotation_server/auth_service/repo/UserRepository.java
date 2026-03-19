package annotation_server.auth_service.repo;

import annotation_server.auth_service.entity.User;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserRepository extends AbstractRepository<User> {
    Optional<User> findByEmail(String email);
}
