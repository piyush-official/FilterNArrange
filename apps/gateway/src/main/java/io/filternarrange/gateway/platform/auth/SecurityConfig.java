// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import io.filternarrange.gateway.platform.web.FeatureGateFilter;
import io.filternarrange.gateway.platform.web.IpRateLimitFilter;
import io.filternarrange.gateway.platform.web.QuotaFilter;
import io.filternarrange.gateway.platform.web.SizeLimitFilter;
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

    @Bean
    public SecurityFilterChain filterChain(
        HttpSecurity http,
        JwtAuthFilter jwt,
        IpRateLimitFilter ipRateLimit,
        SizeLimitFilter sizeLimit,
        QuotaFilter quota,
        FeatureGateFilter featureGate
    ) throws Exception {
        http
            .csrf(c -> c.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(e -> e.authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
            .authorizeHttpRequests(a -> a
                .requestMatchers("/api/v1/auth/signup", "/api/v1/auth/login").permitAll()
                .requestMatchers("/health", "/actuator/**", "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                .anyRequest().authenticated())
            // Plan F §6 — tier filter chain.
            // ipRateLimit runs before auth (covers signup/login).
            // sizeLimit / quota / featureGate run after JWT auth has populated SecurityContext.
            .addFilterBefore(ipRateLimit, UsernamePasswordAuthenticationFilter.class)
            .addFilterBefore(jwt, UsernamePasswordAuthenticationFilter.class)
            .addFilterAfter(sizeLimit, JwtAuthFilter.class)
            .addFilterAfter(quota, SizeLimitFilter.class)
            .addFilterAfter(featureGate, QuotaFilter.class);
        return http.build();
    }
}
