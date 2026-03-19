package annotation_server.chat_service.controller;

import annotation_server.chat_service.service.AbstractService;
import jakarta.persistence.EntityNotFoundException;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public abstract class AbstractController<T, S extends AbstractService<T, ?>> {
    protected final Logger log = LoggerFactory.getLogger(getClass());

    @Autowired
    protected S service;

    @GetMapping
    @ResponseBody
    public ResponseEntity<List<T>> getAll() {
        log.debug("[GET] list all {}") ;
        List<T> items = service.findAll();
        return ResponseEntity.ok(items);
    }

    @GetMapping("/{id}")
    @ResponseBody
    public ResponseEntity<T> getById(@PathVariable Long id) {
        log.debug("[GET] get {} by id={}", resourceName(), id);
        T item = service.getRequired(id);
        return ResponseEntity.ok(item);
    }

    @PostMapping
    @ResponseBody
    public ResponseEntity<T> create(@Valid @RequestBody T body) {
        log.debug("[POST] create {}: {}", resourceName(), body);
        T saved = service.save(body);
        return ResponseEntity.created(URI.create("")) // let concrete controllers override if they want Location
                .body(saved);
    }

    @PutMapping("/{id}")
    @ResponseBody
    public ResponseEntity<T> update(@PathVariable Long id, @Valid @RequestBody T body) {
        log.debug("[PUT] update {} id={}: {}", resourceName(), id, body);
        T updated = service.update(id, body);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        log.debug("[DELETE] delete {} id={}", resourceName(), id);
        service.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    @ExceptionHandler(EntityNotFoundException.class)
    @ResponseBody
    public ResponseEntity<Map<String, Object>> handleNotFound(EntityNotFoundException ex) {
        log.warn("Resource not found: {}", ex.getMessage());
        Map<String, Object> payload = new HashMap<>();
        payload.put("error", "not_found");
        payload.put("message", ex.getMessage());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(payload);
    }

    protected String resourceName() {
        return "resource";
    }
}
