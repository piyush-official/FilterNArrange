// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Duration;
import java.util.Map;
import java.util.Set;

/**
 * Plan F §6 — IP-based rate limit for unauthenticated endpoints (signup, login,
 * password reset). Counts requests per IP per 60-second window; 429 when over.
 */
@Component
public class IpRateLimitFilter extends OncePerRequestFilter {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Set<String> GUARDED_PATHS = Set.of(
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/api/v1/auth/reset"
    );

    private final StringRedisTemplate redis;
    private final int perMinute;

    public IpRateLimitFilter(
        StringRedisTemplate redis,
        @Value("${filternarrange.tier.ip-rate-per-minute:60}") int perMinute
    ) {
        this.redis = redis;
        this.perMinute = perMinute;
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
        String ip = clientIp(req);
        long window = System.currentTimeMillis() / 60_000L;
        String key = "gw:rate:ip:" + ip + ":" + window;
        Long count = redis.opsForValue().increment(key);
        redis.expire(key, Duration.ofMinutes(2));
        if (count != null && count > perMinute) {
            res.setStatus(429);
            res.setHeader("Retry-After", "60");
            res.setContentType("application/json");
            JSON.writeValue(res.getWriter(), Map.of(
                "code", "IP_RATE_LIMITED",
                "message", "Too many requests from this IP. Slow down.",
                "retry_after_seconds", 60
            ));
            return;
        }
        chain.doFilter(req, res);
    }

    private String clientIp(HttpServletRequest req) {
        String fwd = req.getHeader("X-Forwarded-For");
        if (fwd != null && !fwd.isBlank()) {
            int comma = fwd.indexOf(',');
            return comma == -1 ? fwd.trim() : fwd.substring(0, comma).trim();
        }
        return req.getRemoteAddr();
    }
}
