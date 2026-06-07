// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.formatrequest;

import java.time.Instant;
import java.util.UUID;

public record FormatRequest(
    UUID id,
    UUID userId,
    String sampleRef,
    String userLabel,
    Status status,
    int priority,
    Integer githubIssue,
    Instant createdAt,
    Instant resolvedAt
) {
    public enum Status {
        OPEN, TRIAGED, IN_PROGRESS, SHIPPED, REJECTED;

        public String wire() {
            return switch (this) {
                case IN_PROGRESS -> "in-progress";
                default -> name().toLowerCase();
            };
        }

        public static Status fromWire(String s) {
            return switch (s) {
                case "open" -> OPEN;
                case "triaged" -> TRIAGED;
                case "in-progress" -> IN_PROGRESS;
                case "shipped" -> SHIPPED;
                case "rejected" -> REJECTED;
                default -> throw new IllegalArgumentException("Unknown status: " + s);
            };
        }
    }
}
