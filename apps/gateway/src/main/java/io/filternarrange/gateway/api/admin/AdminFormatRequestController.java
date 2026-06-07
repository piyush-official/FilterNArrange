// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.admin;

import io.filternarrange.gateway.application.formatrequest.FormatRequestService;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Plan F §T23 — admin-only triage surface. SecurityConfig restricts
 * ``/api/v1/admin/**`` to authority ``ROLE_ADMIN``.
 */
@RestController
@RequestMapping("/api/v1/admin/format-requests")
public class AdminFormatRequestController {

    private final FormatRequestService svc;

    public AdminFormatRequestController(FormatRequestService svc) {
        this.svc = svc;
    }

    public record TransitionBody(String status, Integer githubIssue) {}

    @GetMapping
    public List<Map<String, Object>> listOpen() {
        return svc.listOpen().stream().map(AdminFormatRequestController::dto).toList();
    }

    @PostMapping("/{id}/transition")
    public ResponseEntity<?> transition(
        @PathVariable UUID id, @RequestBody TransitionBody body
    ) {
        FormatRequest.Status next;
        try {
            next = FormatRequest.Status.fromWire(body.status());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of(
                "code", "INVALID_STATUS",
                "message", e.getMessage()
            ));
        }
        return svc.transition(id, next, body.githubIssue())
            .<ResponseEntity<?>>map(fr -> ResponseEntity.ok(dto(fr)))
            .orElseGet(() -> ResponseEntity.status(404).body(Map.of(
                "code", "FORMAT_REQUEST_NOT_FOUND",
                "message", "Request " + id + " not found."
            )));
    }

    private static Map<String, Object> dto(FormatRequest fr) {
        var m = new java.util.LinkedHashMap<String, Object>();
        m.put("id", fr.id().toString());
        m.put("user_id", fr.userId().toString());
        m.put("sample_ref", fr.sampleRef());
        m.put("user_label", fr.userLabel());
        m.put("status", fr.status().wire());
        m.put("priority", fr.priority());
        m.put("github_issue", fr.githubIssue());
        m.put("created_at", fr.createdAt().toString());
        m.put("resolved_at", fr.resolvedAt() == null ? null : fr.resolvedAt().toString());
        return m;
    }
}
