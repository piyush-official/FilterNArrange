// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collection;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Plan G §T3 — verifies an incoming bearer token against the Keycloak JWKS,
 * upserts the user row, and populates the SecurityContext with the user's
 * canonical UUID as the principal (so {@code CurrentUser.id()} works
 * regardless of the auth provider).
 *
 * <p>Token verification is delegated to {@link JwtDecoder}, which Spring
 * configures from {@code spring.security.oauth2.resourceserver.jwt.jwk-set-uri}
 * pointing at Keycloak's {@code /protocol/openid-connect/certs}.
 */
public class KeycloakAuthFilter extends OncePerRequestFilter {

    private final JwtDecoder jwtDecoder;
    private final KeycloakUserSyncService sync;

    public KeycloakAuthFilter(JwtDecoder jwtDecoder, KeycloakUserSyncService sync) {
        this.jwtDecoder = jwtDecoder;
        this.sync = sync;
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest req, HttpServletResponse res, FilterChain chain
    ) throws ServletException, IOException {
        String header = req.getHeader("Authorization");
        if (header == null || !header.startsWith("Bearer ")) {
            chain.doFilter(req, res);
            return;
        }

        Jwt jwt;
        try {
            jwt = jwtDecoder.decode(header.substring("Bearer ".length()));
        } catch (Exception e) {
            res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            res.setContentType("application/json");
            res.getWriter().write(
                "{\"code\":\"AUTH_INVALID_TOKEN\","
                    + "\"message\":\"Invalid or expired token\"}"
            );
            return;
        }

        String subject = jwt.getSubject();
        String email = jwt.getClaimAsString("email");
        String displayName = jwt.getClaimAsString("preferred_username");
        List<String> roles = extractRealmRoles(jwt);

        UUID userId = sync.upsertOnLogin(subject, email, displayName, roles);

        List<SimpleGrantedAuthority> authorities = roles.stream()
            .map(r -> new SimpleGrantedAuthority(
                "ROLE_" + r.toUpperCase(Locale.ROOT)))
            .collect(Collectors.toList());

        var auth = new UsernamePasswordAuthenticationToken(userId, null, authorities);
        SecurityContextHolder.getContext().setAuthentication(auth);
        chain.doFilter(req, res);
    }

    @SuppressWarnings("unchecked")
    private List<String> extractRealmRoles(Jwt jwt) {
        Map<String, Object> realmAccess = jwt.getClaim("realm_access");
        if (realmAccess == null) return List.of();
        Object roles = realmAccess.get("roles");
        if (!(roles instanceof Collection<?> c)) return List.of();
        return c.stream().map(Object::toString).collect(Collectors.toList());
    }
}
