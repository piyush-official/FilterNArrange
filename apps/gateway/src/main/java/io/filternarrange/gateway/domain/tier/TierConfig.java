// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.tier;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Tier-specific knobs sourced from ``filternarrange.tier`` in application.yml.
 * A value of ``0`` in a daily-ops or upload-size slot means "unlimited" — the
 * filters short-circuit before enforcement when {@link #isUnlimitedOps} /
 * {@link #isUnlimitedUpload} returns true.
 */
@Component
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
