// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.formatrequest;

import io.filternarrange.gateway.application.formatrequest.FormatRequestService;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Plan F §T20 — paid-tier-only endpoint. FeatureGateFilter rejects free
 * users with 403 ``FEATURE_REQUIRES_PAID_TIER``.
 */
@RestController
@RequestMapping("/api/v1/format-requests")
public class FormatRequestController {

    private final FormatRequestService svc;

    public FormatRequestController(FormatRequestService svc) {
        this.svc = svc;
    }

    public record SubmitBody(String sampleRef, String userLabel) {}

    public record FormatRequestDto(
        String id,
        String sampleRef,
        String userLabel,
        String status,
        int priority,
        Integer githubIssue,
        String createdAt
    ) {
        static FormatRequestDto of(FormatRequest fr) {
            return new FormatRequestDto(
                fr.id().toString(),
                fr.sampleRef(),
                fr.userLabel(),
                fr.status().wire(),
                fr.priority(),
                fr.githubIssue(),
                fr.createdAt().toString()
            );
        }
    }

    @PostMapping
    public ResponseEntity<FormatRequestDto> submit(@RequestBody SubmitBody body) {
        FormatRequest fr = svc.submit(
            CurrentUser.id(), body.sampleRef(), body.userLabel()
        );
        return ResponseEntity.status(201).body(FormatRequestDto.of(fr));
    }
}
