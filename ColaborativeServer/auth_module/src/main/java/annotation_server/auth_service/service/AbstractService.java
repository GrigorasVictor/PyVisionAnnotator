package annotation_server.auth_service.service;

import annotation_server.auth_service.repo.AbstractRepository;
import lombok.Getter;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Optional;


@Getter
public abstract class AbstractService<T, R extends AbstractRepository<T>> {
    @Autowired
    protected R repository;

    public T save(T entity) {
        System.out.println(entity);
        return repository.save(entity);
    }

    public void deleteById(Long id) {
        repository.deleteById(id);
    }

    public List<T> findAll() {
        return repository.findAll();
    }

    public Optional<T> findById(Long id) {
        return repository.findById(id);
    }

    public T update(Long id, T entity) {
        return repository.findById(id).isPresent() ?  repository.save(entity) : null;
    }

}
