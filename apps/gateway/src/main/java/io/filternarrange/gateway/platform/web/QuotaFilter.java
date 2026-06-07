// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.platform.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.platform.tier.TierConfig;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Plan F §6 — per-user daily op counter. 429 + Retry-After when the tier's
 * dailyOps cap is exceeded. Operations are counted at HTTP request entry; auth
 * filter must have populated SecurityContext by the time this runs.
 *
 * Exemptions: auth, billing, actuator, admin paths.
 */
@Component
public class QuotaFilter extends OncePerRequestFilter {

    private static final Set<String> EXEMPT_PREFIXES = Set.of(
        "/api/v1/auth/",
        "/api/v1/billing/me",
        "/actuator/",
        "/api/v1/admin/"
    );

    private static final ObjectMapper JSON = new ObjectMapper();

    private final StringRedisTemplate redis;
    private final TierResolver tierResolver;
    private final TierConfig cfg;

    public QuotaFilter(StringRedisTemplate redis, TierResolver tierResolver, TierConfig cfg) {
        this.redis = redis;
        this.tierResolver = tierResolver;
        this.cfg = cfg;
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest req, HttpServletResponse res, FilterChain chain
    ) throws ServletException, IOException {
        String path = req.getRequestURI();
        if (EXEMPT_PREFIXES.stream().anyMatch(path::startsWith)) {
            chain.doFilter(req, res);
            return;
        }
        UUID userId = currentUserId();
        if (userId == null) {
            chain.doFilter(req, res);
            return;
        }
        Tier tier = tierResolver.resolve(userId);
        if (cfg.isUnlimitedOps(tier)) {
            chain.doFilter(req, res);
            return;
        }
        String today = LocalDate.now(ZoneOffset.UTC).toString();
        String key = "gw:rate:user:" + userId + ":ops:" + today;
        Long count = redis.opsForValue().increment(key);
        redis.expire(key, secondsUntilEndOfDayUtc());
        if (count != null && count > cfg.dailyOps(tier)) {
            writeQuotaExceeded(res, tier);
            return;
        }
        chain.doFilter(req, res);
    }

    static UUID currentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || auth.getPrincipal() == null) return null;
        Object principal = auth.getPrincipal();
        if (principal instanceof UUID u) return u;
        try {
            return UUID.fromString(principal.toString());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private Duration secondsUntilEndOfDayUtc() {
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        LocalDateTime midnight = now.toLocalDate().plusDays(1).atStartOfDay();
        return Duration.between(now, midnight);
    }

    private void writeQuotaExceeded(HttpServletResponse res, Tier tier) throws IOException {
        res.setStatus(429);
        res.setHeader("Retry-After", String.valueOf(secondsUntilEndOfDayUtc().toSeconds()));
        res.setContentType("application/json");
        Map<String, Object> body = new java.util.LinkedHashMap<>();
        body.put("code", "TIER_QUOTA_EXCEEDED");
        body.put(
            "message",
            "Daily operation quota exceeded for tier '" + tier.wireValue() + "'."
        );
        body.put("tier", tier.wireValue());
        body.put("upgrade_hint", tier == Tier.FREE ? "/account/billing" : null);
        JSON.writeValue(res.getWriter(), body);
    }
}
