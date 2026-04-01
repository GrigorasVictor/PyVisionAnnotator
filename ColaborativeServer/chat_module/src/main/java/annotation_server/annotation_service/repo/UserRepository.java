package annotation_server.annotation_service.repo;

import annotation_server.annotation_service.entity.User;

import java.util.Optional;

public interface UserRepository extends AbstractRepository<User>{
	Optional<User> findByEmail(String email);
}
