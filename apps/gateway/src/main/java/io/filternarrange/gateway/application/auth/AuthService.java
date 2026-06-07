// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.auth;

import io.filternarrange.gateway.domain.user.User;
import io.filternarrange.gateway.domain.user.UserRepository;
import io.filternarrange.gateway.platform.auth.JwtService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.UUID;

@Service
public class AuthService {

    private final UserRepository users;
    private final PasswordEncoder enc;
    private final JwtService jwt;

    public AuthService(UserRepository users, PasswordEncoder enc, JwtService jwt) {
        this.users = users; this.enc = enc; this.jwt = jwt;
    }

    public record Authenticated(String token, User user) {}

    public Authenticated signup(Credentials c) {
        if (users.findByEmail(c.email()).isPresent())
            throw new IllegalStateException("EMAIL_TAKEN");
        User u = new User(UUID.randomUUID(), c.email(), enc.encode(c.password()),
            c.displayName(), Instant.now(), null);
        u = users.save(u);
        return new Authenticated(jwt.issue(u.id(), u.email()), u);
    }

    public Authenticated login(Credentials c) {
        User u = users.findByEmail(c.email()).orElseThrow(() -> new IllegalStateException("BAD_CREDS"));
        if (!enc.matches(c.password(), u.passwordHash()))
            throw new IllegalStateException("BAD_CREDS");
        return new Authenticated(jwt.issue(u.id(), u.email()), u);
    }

    public User requireUser(UUID id) {
        return users.findById(id).orElseThrow(() -> new IllegalStateException("NO_USER"));
    }
}
