// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.tier;

import java.time.Instant;
import java.util.UUID;

public record Subscription(
    UUID id,
    UUID userId,
    Tier tier,
    Status status,
    Instant startedAt,
    Instant expiresAt,
    String externalRef
) {
    public enum Status { ACTIVE, CANCELLED, EXPIRED }

    public boolean isActiveNow() {
        return status == Status.ACTIVE
            && (expiresAt == null || expiresAt.isAfter(Instant.now()));
    }
}
