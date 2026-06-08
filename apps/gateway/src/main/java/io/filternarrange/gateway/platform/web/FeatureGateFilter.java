// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.infrastructure.messaging.AuditEventPublisher;
import io.filternarrange.gateway.platform.plugin.PluginRegistryService;
import io.filternarrange.gateway.platform.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Plan F §6 — maps the request URL to a plugin_id, looks up the required
 * tier, and rejects free users from paid-only endpoints with a 403 +
 * upgrade_hint envelope.
 */
@Component
public class FeatureGateFilter extends OncePerRequestFilter {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Logger log = LoggerFactory.getLogger(FeatureGateFilter.class);

    private final PluginRegistryService plugins;
    private final TierResolver tierResolver;
    private final AuditEventPublisher audit;

    public FeatureGateFilter(
        PluginRegistryService plugins,
        TierResolver tierResolver,
        AuditEventPublisher audit
    ) {
        this.plugins = plugins;
        this.tierResolver = tierResolver;
        this.audit = audit;
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest req, HttpServletResponse res, FilterChain chain
    ) throws ServletException, IOException {
        String pluginId = resolvePluginId(req);
        if (pluginId == null) {
            chain.doFilter(req, res);
            return;
        }
        Optional<Tier> required = plugins.requiredTier(pluginId);
        if (required.isEmpty() || required.get() == Tier.FREE) {
            chain.doFilter(req, res);
            return;
        }
        UUID userId = QuotaFilter.currentUserId();
        if (userId == null) {
            chain.doFilter(req, res);
            return;
        }
        Tier actual = tierResolver.resolve(userId);
        if (actual == Tier.PAID) {
            chain.doFilter(req, res);
            return;
        }
        res.setStatus(403);
        res.setContentType("application/json");
        JSON.writeValue(res.getWriter(), Map.of(
            "code", "FEATURE_REQUIRES_PAID_TIER",
            "message", "This feature requires a paid subscription.",
            "plugin_id", pluginId,
            "upgrade_hint", "/account/billing"
        ));
        try {
            audit.publish(
                userId,
                "tier-reject",
                req.getMethod() + " " + req.getRequestURI(),
                JSON.valueToTree(Map.of(
                    "reason", "FEATURE_REQUIRES_PAID_TIER",
                    "plugin_id", pluginId,
                    "tier", actual.wireValue()
                )),
                UUID.randomUUID().toString()
            );
        } catch (Exception e) {
            log.warn("tier-reject audit emit failed: {}", e.toString());
        }
    }

    private String resolvePluginId(HttpServletRequest req) {
        Object attr = req.getAttribute("plugin.id");
        if (attr instanceof String s) return s;

        String path = req.getRequestURI();
        if (path.startsWith("/api/v1/ai/nl-to-filter"))  return "ai-nl-to-filter";
        if (path.startsWith("/api/v1/ai/summary"))       return "ai-auto-summary";
        if (path.startsWith("/api/v1/ai/chart-suggest")) return "ai-chart-suggest";
        if (path.startsWith("/api/v1/ai/anomaly"))       return "ai-anomaly-detect";
        if (path.startsWith("/api/v1/recipes"))          return "recipe-crud";
        if (path.equals("/api/v1/format-requests") && "POST".equals(req.getMethod())) {
            return "format-request-submit";
        }
        return null;
    }
}
