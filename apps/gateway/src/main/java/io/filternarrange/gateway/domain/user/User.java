// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.user;

import java.time.Instant;
import java.util.UUID;

public record User(UUID id, String email, String passwordHash, String displayName,
                   Instant createdAt, Instant lastLoginAt) {}
