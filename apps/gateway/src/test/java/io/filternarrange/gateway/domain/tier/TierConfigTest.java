// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.tier;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class TierConfigTest {

    @Test
    void freeTierLimitsFromConfig() {
        TierConfig cfg = new TierConfig(5, 100, 50, 0);
        assertThat(cfg.maxUploadMb(Tier.FREE)).isEqualTo(5);
        assertThat(cfg.dailyOps(Tier.FREE)).isEqualTo(100);
    }

    @Test
    void paidTierZeroMeansUnlimited() {
        TierConfig cfg = new TierConfig(5, 100, 50, 0);
        assertThat(cfg.dailyOps(Tier.PAID)).isZero();
        assertThat(cfg.isUnlimitedOps(Tier.PAID)).isTrue();
    }

    @Test
    void tierFromStringIsCaseInsensitive() {
        assertThat(Tier.fromString("FREE")).isEqualTo(Tier.FREE);
        assertThat(Tier.fromString("paid")).isEqualTo(Tier.PAID);
    }

    @Test
    void subscriptionIsActiveOnlyWhenStatusActiveAndNotExpired() {
        java.time.Instant past = java.time.Instant.now().minusSeconds(60);
        java.util.UUID id = java.util.UUID.randomUUID();
        var s = new Subscription(id, id, Tier.PAID,
            Subscription.Status.ACTIVE, past, past, null);
        assertThat(s.isActiveNow()).isFalse();
        var s2 = new Subscription(id, id, Tier.PAID,
            Subscription.Status.ACTIVE, past, null, null);
        assertThat(s2.isActiveNow()).isTrue();
    }
}
