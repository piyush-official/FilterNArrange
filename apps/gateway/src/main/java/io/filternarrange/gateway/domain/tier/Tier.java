// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.tier;

import java.util.Locale;

public enum Tier {
    FREE, PAID;

    public static Tier fromString(String raw) {
        if (raw == null) return FREE;
        return switch (raw.toLowerCase(Locale.ROOT)) {
            case "paid" -> PAID;
            case "free" -> FREE;
            default -> throw new IllegalArgumentException("Unknown tier: " + raw);
        };
    }

    public String wireValue() {
        return name().toLowerCase(Locale.ROOT);
    }
}
