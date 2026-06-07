// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.auth;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Plan G §T5 — public endpoint the frontend hits before mounting the
 * login UI to discover which auth provider is in use. Lets us flip
 * AUTH_PROVIDER at deploy time without rebuilding the SPA.
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthConfigController {

    private final String authProvider;
    private final String keycloakIssuer;
    private final String keycloakClientId;

    public AuthConfigController(
        @Value("${AUTH_PROVIDER:spring-jwt}") String authProvider,
        @Value("${keycloak.issuer-uri:http://localhost:8085/realms/filternarrange}") String issuer,
        @Value("${keycloak.frontend-client-id:filternarrange-frontend}") String clientId
    ) {
        this.authProvider = authProvider;
        this.keycloakIssuer = issuer;
        this.keycloakClientId = clientId;
    }

    @GetMapping("/config")
    public Map<String, Object> config() {
        var body = new LinkedHashMap<String, Object>();
        body.put("provider", authProvider);
        if ("keycloak".equalsIgnoreCase(authProvider)) {
            body.put("issuer", keycloakIssuer);
            body.put("client_id", keycloakClientId);
        }
        return body;
    }
}
