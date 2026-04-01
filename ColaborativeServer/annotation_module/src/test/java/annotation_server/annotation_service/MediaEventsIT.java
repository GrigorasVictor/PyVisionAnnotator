package annotation_server.annotation_service;

import annotation_server.annotation_service.dto.WsEventEnvelope;
import annotation_server.annotation_service.support.TestJwtFactory;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class MediaEventsIT {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private SimpMessagingTemplate messagingTemplate;

    @Test
    void uploadImagePublishesImageAvailableEvent() throws Exception {
        byte[] png = new byte[] {
                (byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
                0x08, 0x02, 0x00, 0x00, 0x00, (byte) 0x90, 0x77, 0x53,
                (byte) 0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
                0x54, 0x08, (byte) 0xD7, 0x63, (byte) 0xF8, (byte) 0xCF, (byte) 0xC0, 0x00,
                0x00, 0x04, 0x00, 0x01, (byte) 0xE2, 0x26, 0x05, (byte) 0x9B,
                0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
                (byte) 0xAE, 0x42, 0x60, (byte) 0x82
        };

        MockMultipartFile file = new MockMultipartFile("file", "img.png", "image/png", png);

        mockMvc.perform(multipart("/media/upload-temp")
                        .file(file)
                        .param("sessionId", "sess_001")
                        .param("projectId", "proj_alpha")
                        .param("imageId", "img_0001")
                        .param("cameraId", "cam_entrance_01")
                        .header(HttpHeaders.AUTHORIZATION, TestJwtFactory.bearerFor("stef@gmail.com")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId").value("sess_001"))
                .andExpect(jsonPath("$.cameraId").value("cam_entrance_01"))
                .andExpect(jsonPath("$.downloadUrl").exists());

        ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
        verify(messagingTemplate).convertAndSend(eq("/topic/sessions/sess_001"), payloadCaptor.capture());

        WsEventEnvelope event = (WsEventEnvelope) payloadCaptor.getValue();
        assertEquals("image.available", event.type());
        assertEquals("sess_001", event.sessionId());
    }
}


