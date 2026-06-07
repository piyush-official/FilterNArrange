// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Plan F refactor — @WebMvcTest slice no longer composes cleanly with the
 * tier filter chain (filters require StringRedisTemplate / TierResolver /
 * PluginRegistryService / TierConfig, plus @ConfigurationPropertiesScan).
 * Switched to @SpringBootTest + Testcontainers, matching the other Spring
 * tests in this codebase.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class HealthControllerTest {

    @Container
    static PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @Container
    static MinIOContainer MINIO =
        new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        r.add("spring.datasource.username", POSTGRES::getUsername);
        r.add("spring.datasource.password", POSTGRES::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
    }

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
            .andExpect(status().isOk())
            .andExpect(content().contentTypeCompatibleWith("application/json"))
            .andExpect(jsonPath("$.status").value("UP"));
    }
}
