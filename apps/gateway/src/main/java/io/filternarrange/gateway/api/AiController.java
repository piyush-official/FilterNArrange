// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api;

import io.filternarrange.gateway.application.AiService;
import io.filternarrange.gateway.infrastructure.http.AiCapabilityDisabledException;
import io.filternarrange.gateway.infrastructure.http.AiUpstreamException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/ai")
public class AiController {

    private final AiService svc;

    public AiController(AiService svc) {
        this.svc = svc;
    }

    @PostMapping("/nl-to-filter")
    public Map<String, Object> nlToFilter(@RequestBody Map<String, Object> body) {
        return svc.nlToFilter(body);
    }

    @PostMapping("/summary")
    public Map<String, Object> summary(@RequestBody Map<String, Object> body) {
        return svc.summary(body);
    }

    @PostMapping("/chart-suggest")
    public Map<String, Object> chartSuggest(@RequestBody Map<String, Object> body) {
        return svc.chartSuggest(body);
    }

    @PostMapping("/anomaly")
    public Map<String, Object> anomaly(@RequestBody Map<String, Object> body) {
        return svc.anomaly(body);
    }

    @ExceptionHandler(AiCapabilityDisabledException.class)
    public ResponseEntity<Map<String, Object>> disabled(AiCapabilityDisabledException exc) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(envelope("AI_CAPABILITY_DISABLED", exc.getMessage()));
    }

    @ExceptionHandler(AiUpstreamException.class)
    public ResponseEntity<Map<String, Object>> upstream(AiUpstreamException exc) {
        HttpStatus status = switch (exc.statusCode()) {
            case 404 -> HttpStatus.NOT_FOUND;
            case 504 -> HttpStatus.GATEWAY_TIMEOUT;
            default  -> HttpStatus.BAD_GATEWAY;
        };
        String code = String.valueOf(
            exc.detail().getOrDefault("code", "AI_UPSTREAM_ERROR")
        );
        return ResponseEntity.status(status).body(envelope(code, exc.getMessage()));
    }

    private Map<String, Object> envelope(String code, String message) {
        return Map.of(
            "code", code,
            "plugin_id", "",
            "message", message == null ? "" : message,
            "trace_id", UUID.randomUUID().toString()
        );
    }
}
