package annotation_server.annotation_service.controller;

import annotation_server.annotation_service.dto.ImageMetaDto;
import annotation_server.annotation_service.dto.EventType;
import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.entity.TempImageData;
import annotation_server.annotation_service.service.CollaborationService;
import annotation_server.annotation_service.service.TempImageStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.util.DigestUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.UUID;

@RestController
@RequestMapping("/media")
public class MediaController {

    private static final Logger log = LoggerFactory.getLogger(MediaController.class);

    private final CollaborationService collaborationService;
    private final TempImageStore tempImageStore;
    private final SimpMessagingTemplate messagingTemplate;
    private final Duration mediaTtl;

    public MediaController(CollaborationService collaborationService,
                           TempImageStore tempImageStore,
                           SimpMessagingTemplate messagingTemplate,
                           @org.springframework.beans.factory.annotation.Value("${collab.media-ttl:PT4H}") Duration mediaTtl) {
        this.collaborationService = collaborationService;
        this.tempImageStore = tempImageStore;
        this.messagingTemplate = messagingTemplate;
        this.mediaTtl = mediaTtl;
    }

    @PostMapping(path = "/upload-temp", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ImageMetaDto uploadTemp(
            @RequestParam String sessionId,
            @RequestParam String projectId,
            @RequestParam String imageId,
            @RequestParam String cameraId,
            @RequestParam(required = false) String name,
            @RequestParam("file") MultipartFile file,
            Authentication authentication
    ) throws IOException {
        String actor = authentication == null ? "" : String.valueOf(authentication.getPrincipal()).toLowerCase();
        log.info("media.upload.in sessionId={} projectId={} imageId={} cameraId={} actor={} fileName={} sizeBytes={}",
                sessionId,
                projectId,
                imageId,
                cameraId,
                actor,
                file.getOriginalFilename(),
                file.getSize());

        if (file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "file is required");
        }

        byte[] bytes = file.getBytes();
        BufferedImage image = ImageIO.read(new ByteArrayInputStream(bytes));
        if (image == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Uploaded file is not a valid image");
        }

        collaborationService.ensureSession(sessionId, projectId, imageId, cameraId,
                name == null || name.isBlank() ? sessionId : name);

        if (!actor.isBlank()) {
            try {
                collaborationService.requireMember(sessionId, actor);
            } catch (IllegalArgumentException ex) {
                // First upload on a new session can bootstrap membership for actor.
                collaborationService.markUser(sessionId, actor, "EDITOR", "ONLINE");
                log.info("media.upload.membership_bootstrap sessionId={} actor={}", sessionId, actor);
            }
        }

        String token = DigestUtils.md5DigestAsHex((imageId + UUID.randomUUID()).getBytes(StandardCharsets.UTF_8));
        Instant expiresAt = Instant.now().plus(mediaTtl);
        String fileName = file.getOriginalFilename() == null ? imageId : file.getOriginalFilename();
        String mimeType = file.getContentType() == null ? MediaType.APPLICATION_OCTET_STREAM_VALUE : file.getContentType();

        ImageMetaDto meta = new ImageMetaDto(
                sessionId,
                imageId,
                cameraId,
                fileName,
                mimeType,
                bytes.length,
                image.getWidth(),
                image.getHeight(),
                sha256(bytes),
                "/media/temp/" + imageId + "?token=" + token,
                expiresAt
        );

        tempImageStore.put(imageId, new TempImageData(bytes, token, meta));

        messagingTemplate.convertAndSend(
                "/topic/sessions/" + sessionId,
                collaborationService.buildImageAvailableEvent(sessionId, meta, actor.isBlank() ? "system" : actor)
        );

        WsEventEnvelope sessionUpdated = collaborationService.buildSessionListEvent(
                EventType.SESSION_UPDATED.value(),
                sessionId,
                actor,
                "image_upload"
        );
        messagingTemplate.convertAndSend("/topic/sessions", sessionUpdated);

        log.info("media.upload.out sessionId={} imageId={} cameraId={} actor={} destination={} expiresAt={}",
                sessionId,
                imageId,
                cameraId,
                actor.isBlank() ? "system" : actor,
                "/topic/sessions/" + sessionId,
                expiresAt);
        log.info("ws.event.out eventId={} type={} sessionId={} actor={} version={} destination={}",
                sessionUpdated.eventId(),
                sessionUpdated.type(),
                sessionUpdated.sessionId(),
                sessionUpdated.actorId(),
                sessionUpdated.version(),
                "/topic/sessions");

        return meta;
    }

    @GetMapping("/temp/{imageId}")
    public ResponseEntity<byte[]> getTempImage(@PathVariable String imageId, @RequestParam String token) {
        log.info("media.download.in imageId={}", imageId);
        TempImageData imageData = tempImageStore.get(imageId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Image not found"));

        if (!imageData.token().equals(token) || imageData.metadata().expiresAt().isBefore(Instant.now())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid or expired token");
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType(imageData.metadata().mimeType()));
        headers.setContentDisposition(ContentDisposition.inline().filename(imageData.metadata().fileName()).build());
        log.info("media.download.out imageId={} mimeType={} sizeBytes={}",
                imageId,
                imageData.metadata().mimeType(),
                imageData.content().length);
        return new ResponseEntity<>(imageData.content(), headers, HttpStatus.OK);
    }

    private String sha256(byte[] data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(data));
        } catch (Exception ex) {
            throw new IllegalStateException(ex);
        }
    }
}


