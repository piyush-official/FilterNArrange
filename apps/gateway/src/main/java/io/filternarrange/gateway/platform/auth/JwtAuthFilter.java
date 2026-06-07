// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;
import java.util.UUID;

public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtService jwt;
    public JwtAuthFilter(JwtService jwt) { this.jwt = jwt; }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String auth = req.getHeader("Authorization");
        if (auth != null && auth.startsWith("Bearer ")) {
            try {
                UUID userId = jwt.verify(auth.substring(7));
                var token = new UsernamePasswordAuthenticationToken(
                    userId, null, List.of());
                SecurityContextHolder.getContext().setAuthentication(token);
            } catch (Exception ignored) { /* fall through unauthenticated */ }
        }
        chain.doFilter(req, res);
    }
}
