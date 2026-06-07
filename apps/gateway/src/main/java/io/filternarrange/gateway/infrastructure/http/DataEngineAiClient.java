// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.http;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * Thin pass-through to the data-engine {@code /ai/*} endpoints (Plan E §T16).
 *
 * <p>Reuses the {@code dataEngine} circuit-breaker established by Plan B so a
 * flapping data-engine trips the same way for AI traffic as it does for the
 * sync filter/convert path. 404s with {@code code=AI_CAPABILITY_DISABLED}
 * surface as {@link AiCapabilityDisabledException}; other upstream errors
 * surface as {@link AiUpstreamException} so the controller can map them
 * back to a public HTTP envelope.
 */
@Component
public class DataEngineAiClient {

    private final RestClient rest;

    public DataEngineAiClient(
        @Qualifier("dataEngineRestClient") RestClient dataEngineRestClient
    ) {
        this.rest = dataEngineRestClient;
    }

    @CircuitBreaker(name = "dataEngine")
    public Map<String, Object> nlToFilter(Map<String, Object> req) {
        return post("/ai/nl-to-filter", req);
    }

    @CircuitBreaker(name = "dataEngine")
    public Map<String, Object> summary(Map<String, Object> req) {
        return post("/ai/summary", req);
    }

    @CircuitBreaker(name = "dataEngine")
    public Map<String, Object> chartSuggest(Map<String, Object> req) {
        return post("/ai/chart-suggest", req);
    }

    @CircuitBreaker(name = "dataEngine")
    public Map<String, Object> anomaly(Map<String, Object> req) {
        return post("/ai/anomaly", req);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> post(String path, Map<String, Object> body) {
        ResponseEntity<Map> resp = rest.post()
            .uri(path)
            .body(body)
            .retrieve()
            .onStatus(HttpStatusCode::isError, (request, response) -> {
                Map<String, Object> envelope = parseDetail(response.getBody().readAllBytes());
                int code = response.getStatusCode().value();
                if (code == 404 && "AI_CAPABILITY_DISABLED"
                        .equals(String.valueOf(envelope.getOrDefault("code", "")))) {
                    throw new AiCapabilityDisabledException(envelope);
                }
                throw new AiUpstreamException(code, envelope);
            })
            .toEntity(Map.class);
        return resp.getBody();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseDetail(byte[] raw) {
        try {
            Map<String, Object> body = new com.fasterxml.jackson.databind.ObjectMapper()
                .readValue(raw, Map.class);
            Object detail = body.get("detail");
            if (detail instanceof Map<?, ?> d) {
                return (Map<String, Object>) d;
            }
            return body;
        } catch (Exception e) {
            return Map.of("code", "AI_UPSTREAM_ERROR", "message", new String(raw));
        }
    }
}
