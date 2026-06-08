// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import io.filternarrange.gateway.platform.web.FeatureGateFilter;
import io.filternarrange.gateway.platform.web.IpRateLimitFilter;
import io.filternarrange.gateway.platform.web.QuotaFilter;
import io.filternarrange.gateway.platform.web.SizeLimitFilter;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.http.HttpStatus;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }

    @Bean
    public JwtAuthFilter jwtAuthFilter(JwtService jwtService) {
        return new JwtAuthFilter(jwtService);
    }

    /**
     * Plan G §T3 — chain picks the auth filter from AUTH_PROVIDER:
     *   spring-jwt (default) → JwtAuthFilter
     *   keycloak             → KeycloakAuthFilter (only constructed when AuthConfig fires)
     * KeycloakAuthFilter is injected via ObjectProvider so the bean's absence
     * in spring-jwt mode is fine.
     */
    @Bean
    public SecurityFilterChain filterChain(
        HttpSecurity http,
        JwtAuthFilter jwt,
        ObjectProvider<KeycloakAuthFilter> keycloak,
        IpRateLimitFilter ipRateLimit,
        SizeLimitFilter sizeLimit,
        QuotaFilter quota,
        FeatureGateFilter featureGate,
        @Value("${AUTH_PROVIDER:spring-jwt}") String authProvider
    ) throws Exception {
        http
            .csrf(c -> c.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(e -> e.authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
            .authorizeHttpRequests(a -> a
                .requestMatchers("/api/v1/auth/signup", "/api/v1/auth/login", "/api/v1/auth/config").permitAll()
                .requestMatchers("/health", "/actuator/**", "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                .anyRequest().authenticated())
            .addFilterBefore(ipRateLimit, UsernamePasswordAuthenticationFilter.class);

        if ("keycloak".equalsIgnoreCase(authProvider)) {
            KeycloakAuthFilter k = keycloak.getIfAvailable();
            if (k == null) {
                throw new IllegalStateException(
                    "AUTH_PROVIDER=keycloak but KeycloakAuthFilter is not on the classpath / "
                        + "AuthConfig didn't fire. Check keycloak.jwks-uri."
                );
            }
            http.addFilterBefore(k, UsernamePasswordAuthenticationFilter.class)
                .addFilterAfter(sizeLimit, KeycloakAuthFilter.class);
        } else {
            http.addFilterBefore(jwt, UsernamePasswordAuthenticationFilter.class)
                .addFilterAfter(sizeLimit, JwtAuthFilter.class);
        }

        http.addFilterAfter(quota, SizeLimitFilter.class)
            .addFilterAfter(featureGate, QuotaFilter.class);
        return http.build();
    }
}
