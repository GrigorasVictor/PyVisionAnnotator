package annotation_server.annotation_service.service;

import annotation_server.annotation_service.repo.AbstractRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.Getter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;


@Getter
public abstract class AbstractService<T, R extends AbstractRepository<T>> {
    @Autowired
    protected R repository;

    protected final Logger log = LoggerFactory.getLogger(getClass());

    @Transactional
    public T save(T entity) {
        log.debug("Saving entity: {}", entity);
        T saved = repository.save(entity);
        log.debug("Saved entity: {}", saved);
        return saved;
    }

    @Transactional(readOnly = true)
    public List<T> findAll() {
        log.debug("Fetching all entities");
        return repository.findAll();
    }

    @Transactional(readOnly = true)
    public Optional<T> findById(Long id) {
        log.debug("Fetching entity by id={}", id);
        return repository.findById(id);
    }

    @Transactional(readOnly = true)
    public T getRequired(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Entity not found: " + id));
    }

    @Transactional
    public T update(Long id, T entity) {
        log.debug("Updating entity id={}", id);
        if (!repository.existsById(id)) {
            throw new EntityNotFoundException("Entity not found: " + id);
        }
        T updated = repository.save(entity);
        log.debug("Updated entity id={}", id);
        return updated;
    }

    @Transactional
    public void deleteById(Long id) {
        log.debug("Deleting entity id={}", id);
        if (!repository.existsById(id)) {
            throw new EntityNotFoundException("Entity not found: " + id);
        }
        repository.deleteById(id);
        log.debug("Deleted entity id={}", id);
    }

    @Transactional(readOnly = true)
    public boolean exists(Long id) {
        return repository.existsById(id);
    }
}


