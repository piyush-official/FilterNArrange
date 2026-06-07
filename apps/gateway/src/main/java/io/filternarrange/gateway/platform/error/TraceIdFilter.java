// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.error;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceIdFilter extends OncePerRequestFilter {
    public static final String KEY = "traceId";

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String existing = req.getHeader("X-Trace-Id");
        String id = (existing != null && !existing.isBlank()) ? existing : UUID.randomUUID().toString();
        MDC.put(KEY, id);
        res.setHeader("X-Trace-Id", id);
        try { chain.doFilter(req, res); } finally { MDC.remove(KEY); }
    }

    public static String current() {
        String v = MDC.get(KEY);
        return v == null ? "unknown" : v;
    }
}
