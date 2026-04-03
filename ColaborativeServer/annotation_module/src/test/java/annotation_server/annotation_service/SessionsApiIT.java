package annotation_server.annotation_service;

import annotation_server.annotation_service.service.CollaborationService;
import annotation_server.annotation_service.support.TestJwtFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class SessionsApiIT {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private CollaborationService collaborationService;

    @BeforeEach
    void setUp() {
        collaborationService.ensureSession("sess_001", "proj_alpha", "img_0001", "cam_entrance_01", "Entrance");
        collaborationService.markUser("sess_001", "stef@gmail.com", "EDITOR", "ONLINE");
        collaborationService.markUser("sess_001", "victor@gmail.com", "VIEWER", "OFFLINE");
    }

    @Test
    void getSessionsReturnsCameraIdAndUsers() throws Exception {
        mockMvc.perform(get("/sessions")
                        .header(HttpHeaders.AUTHORIZATION, TestJwtFactory.bearerFor("stef@gmail.com")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].sessionId").value("sess_001"))
                .andExpect(jsonPath("$.items[0].cameraId").value("cam_entrance_01"))
                .andExpect(jsonPath("$.items[0].users[0].userId").exists())
                .andExpect(jsonPath("$.items[0].users.length()").value(2));
    }

    @Test
    void createSessionReturnsRandomRoomCodeAndAddsCreator() throws Exception {
        mockMvc.perform(post("/sessions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Camera room\"}")
                        .header(HttpHeaders.AUTHORIZATION, TestJwtFactory.bearerFor("ana@gmail.com")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId", matchesPattern("^[a-z0-9]{5}$")))
                .andExpect(jsonPath("$.name").value("Camera room"));
    }

    @Test
    void snapshotAutoAddsAuthenticatedUserAsSessionMember() throws Exception {
        mockMvc.perform(get("/sessions/sess_001/snapshot")
                        .header(HttpHeaders.AUTHORIZATION, TestJwtFactory.bearerFor("alex@gmail.com")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId").value("sess_001"))
                .andExpect(jsonPath("$.users[?(@.userId=='alex@gmail.com')]").exists());
    }
}

