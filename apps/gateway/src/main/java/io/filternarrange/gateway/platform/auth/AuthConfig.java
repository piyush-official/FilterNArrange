// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;

/**
 * Plan G §T3 — exposes the {@code JwtDecoder} bean only when
 * {@code AUTH_PROVIDER=keycloak}. In spring-jwt mode the bean isn't
 * created at all, so the OAuth2 resource server starter stays inert.
 */
@Configuration
@ConditionalOnProperty(name = "AUTH_PROVIDER", havingValue = "keycloak")
public class AuthConfig {

    @Bean
    public JwtDecoder jwtDecoder(
        @Value("${keycloak.jwks-uri:http://keycloak:8080/realms/filternarrange/protocol/openid-connect/certs}")
        String jwksUri
    ) {
        return NimbusJwtDecoder.withJwkSetUri(jwksUri).build();
    }

    @Bean
    public KeycloakAuthFilter keycloakAuthFilter(
        JwtDecoder jwtDecoder, KeycloakUserSyncService sync
    ) {
        return new KeycloakAuthFilter(jwtDecoder, sync);
    }
}
