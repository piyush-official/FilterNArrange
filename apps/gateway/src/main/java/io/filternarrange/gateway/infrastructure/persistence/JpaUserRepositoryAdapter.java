// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.user.User;
import io.filternarrange.gateway.domain.user.UserRepository;
import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.UUID;

@Component
public class JpaUserRepositoryAdapter implements UserRepository {

    private final UserJpaRepository jpa;
    public JpaUserRepositoryAdapter(UserJpaRepository jpa) { this.jpa = jpa; }

    @Override public User save(User u) {
        UserEntity e = new UserEntity(
            u.id(), u.email(), u.passwordHash(), u.displayName(),
            u.createdAt(), u.lastLoginAt());
        UserEntity saved = jpa.save(e);
        return toDomain(saved);
    }
    @Override public Optional<User> findByEmail(String email) {
        return jpa.findByEmailIgnoreCase(email).map(this::toDomain);
    }
    @Override public Optional<User> findById(UUID id) {
        return jpa.findById(id).map(this::toDomain);
    }
    private User toDomain(UserEntity e) {
        return new User(e.getId(), e.getEmail(), e.getPasswordHash(), e.getDisplayName(),
            e.getCreatedAt(), e.getLastLoginAt());
    }
}
