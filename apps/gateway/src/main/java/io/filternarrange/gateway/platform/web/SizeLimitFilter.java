// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.domain.tier.TierConfig;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Plan F §6 — pre-flight body-size check against the tier's max-upload-MB.
 * Only the Content-Length header is inspected; the request body is not consumed.
 */
@Component
public class SizeLimitFilter extends OncePerRequestFilter {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Set<String> GUARDED_PATHS = Set.of(
        "/api/v1/uploads",
        "/api/v1/detect",
        "/api/v1/paste",
        "/api/v1/jobs"
    );

    private final TierResolver tierResolver;
    private final TierConfig cfg;

    public SizeLimitFilter(TierResolver tierResolver, TierConfig cfg) {
        this.tierResolver = tierResolver;
        this.cfg = cfg;
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest req, HttpServletResponse res, FilterChain chain
    ) throws ServletException, IOException {
        String path = req.getRequestURI();
        if (GUARDED_PATHS.stream().noneMatch(path::startsWith)) {
            chain.doFilter(req, res);
            return;
        }
        UUID userId = QuotaFilter.currentUserId();
        if (userId == null) {
            chain.doFilter(req, res);
            return;
        }
        Tier tier = tierResolver.resolve(userId);
        if (cfg.isUnlimitedUpload(tier)) {
            chain.doFilter(req, res);
            return;
        }
        long maxBytes = cfg.maxUploadMb(tier) * 1024L * 1024L;
        long len = req.getContentLengthLong();
        if (len > maxBytes) {
            res.setStatus(413);
            res.setContentType("application/json");
            Map<String, Object> body = new java.util.LinkedHashMap<>();
            body.put("code", "PAYLOAD_TOO_LARGE");
            body.put(
                "message",
                "File exceeds tier limit of " + cfg.maxUploadMb(tier) + " MB."
            );
            body.put("tier", tier.wireValue());
            body.put("max_upload_mb", cfg.maxUploadMb(tier));
            body.put(
                "upgrade_hint", tier == Tier.FREE ? "/account/billing" : null
            );
            JSON.writeValue(res.getWriter(), body);
            return;
        }
        chain.doFilter(req, res);
    }
}
