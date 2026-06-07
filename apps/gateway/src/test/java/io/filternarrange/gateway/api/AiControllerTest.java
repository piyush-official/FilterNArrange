// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api;

import io.filternarrange.gateway.application.AiService;
import io.filternarrange.gateway.infrastructure.http.AiCapabilityDisabledException;
import io.filternarrange.gateway.infrastructure.http.AiUpstreamException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Pure controller-slice tests — no Spring context bootstrap. Avoids dragging
 * Flyway / Testcontainers into a test that only exercises HTTP-to-service
 * mapping.
 */
class AiControllerTest {

    private AiService service;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        service = mock(AiService.class);
        mvc = MockMvcBuilders.standaloneSetup(new AiController(service)).build();
    }

    @Test
    void postNlToFilter_returnsResult() throws Exception {
        when(service.nlToFilter(any())).thenReturn(
            Map.of("filter_spec", Map.of("kind", "row"), "confidence", 0.9)
        );
        mvc.perform(post("/api/v1/ai/nl-to-filter")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"ref\":\"x\",\"query\":\"q\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.confidence").value(0.9));
    }

    @Test
    void disabledCapability_returns404WithEnvelope() throws Exception {
        when(service.anomaly(any())).thenThrow(
            new AiCapabilityDisabledException(Map.of(
                "code", "AI_CAPABILITY_DISABLED", "message", "off"
            ))
        );
        mvc.perform(post("/api/v1/ai/anomaly")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"ref\":\"x\"}"))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.code").value("AI_CAPABILITY_DISABLED"));
    }

    @Test
    void upstreamError_maps_502() throws Exception {
        when(service.summary(any())).thenThrow(
            new AiUpstreamException(502, Map.of(
                "code", "AI_LLM_OUTPUT_INVALID", "message", "bad"
            ))
        );
        mvc.perform(post("/api/v1/ai/summary")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"ref\":\"x\"}"))
            .andExpect(status().isBadGateway())
            .andExpect(jsonPath("$.code").value("AI_LLM_OUTPUT_INVALID"));
    }
}
