// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.tier;

import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Tier-specific knobs sourced from ``filternarrange.tier`` in application.yml.
 * A value of ``0`` in a daily-ops or upload-size slot means "unlimited" — the
 * filters short-circuit before enforcement when {@link #isUnlimitedOps} /
 * {@link #isUnlimitedUpload} returns true.
 *
 * <p>Registered via {@code @ConfigurationPropertiesScan} on
 * {@code GatewayApplication} — records can't have a no-arg constructor, so
 * {@code @Component} would fail bean instantiation.
 */
@ConfigurationProperties(prefix = "filternarrange.tier")
public record TierConfig(
    int freeTierMaxUploadMb,
    int freeTierDailyOps,
    int paidTierMaxUploadMb,
    int paidTierDailyOps
) {
    public int maxUploadMb(Tier t) {
        return t == Tier.PAID ? paidTierMaxUploadMb : freeTierMaxUploadMb;
    }

    public int dailyOps(Tier t) {
        return t == Tier.PAID ? paidTierDailyOps : freeTierDailyOps;
    }

    public boolean isUnlimitedOps(Tier t) {
        return dailyOps(t) == 0;
    }

    public boolean isUnlimitedUpload(Tier t) {
        return maxUploadMb(t) == 0;
    }
}
