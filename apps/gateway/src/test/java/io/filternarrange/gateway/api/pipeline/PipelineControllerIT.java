// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.pipeline;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.dataengine.DataEngineClient;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class PipelineControllerIT {

    @Container static PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine");
    @Container static MinIOContainer MINIO = new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", PG::getUsername);
        r.add("spring.datasource.password", PG::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
    }

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @MockBean DataEngineClient engine;

    private String authToken() throws Exception {
        String body = mvc.perform(post("/api/v1/auth/signup")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"email":"p@x.co","password":"hunter2hunter2"}"""))
            .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return json.readTree(body).get("token").asText();
    }

    @Test
    void uploadDetectFilterConvertDownload() throws Exception {
        String token = authToken();
        var file = new MockMultipartFile("file", "x.csv", "text/csv",
            "name,age\nA,1\nB,2".getBytes());
        String upRes = mvc.perform(multipart("/api/v1/upload").file(file)
                .header("Authorization", "Bearer " + token))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.uploadId").isString())
            .andReturn().getResponse().getContentAsString();
        JsonNode up = json.readTree(upRes);
        String uploadId = up.get("uploadId").asText();

        Mockito.when(engine.detect(Mockito.any())).thenReturn(
            new EngineDtos.DetectResult("csv", 0.95, List.of(
                new EngineDtos.Column("name", "string", false),
                new EngineDtos.Column("age", "integer", false))));
        mvc.perform(post("/api/v1/detect")
                .header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"uploadId":"%s"}""".formatted(uploadId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.format").value("csv"));

        Mockito.when(engine.preview(Mockito.any())).thenReturn(
            new EngineDtos.FilterResult(
                List.of(new EngineDtos.Column("name", "string", false)),
                List.of(Map.of("name", "A"), Map.of("name", "B"))));
        mvc.perform(post("/api/v1/filter/preview")
                .header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"uploadId":"%s","filter":{"kind":"column","keep":["name"]},"sampleSize":10}
                    """.formatted(uploadId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.rows.length()").value(2));

        Mockito.when(engine.convert(Mockito.any())).thenReturn(
            new EngineDtos.ConvertResult("results/users/x/abc.json"));
        String convRes = mvc.perform(post("/api/v1/convert")
                .header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"uploadId":"%s","filter":{"kind":"column","keep":["name"]},"outputFormat":"json"}
                    """.formatted(uploadId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.resultId").isString())
            .andReturn().getResponse().getContentAsString();
        String resultId = json.readTree(convRes).get("resultId").asText();

        mvc.perform(get("/api/v1/download/" + resultId)
                .header("Authorization", "Bearer " + token))
            .andExpect(status().is3xxRedirection());
    }
}
