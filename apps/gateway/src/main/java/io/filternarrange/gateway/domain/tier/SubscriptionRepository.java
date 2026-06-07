// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.tier;

import java.util.Optional;
import java.util.UUID;

public interface SubscriptionRepository {
    Optional<Subscription> findActiveByUserId(UUID userId);

    Subscription save(Subscription sub);
}
