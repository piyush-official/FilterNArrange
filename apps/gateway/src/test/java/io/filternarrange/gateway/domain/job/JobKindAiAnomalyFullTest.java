// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.job;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Plan E §T19 — the ai-anomaly-full job kind is recognized by the
 * JobKind enum and round-trips through the wire-name mapping.
 */
class JobKindAiAnomalyFullTest {

    @Test
    void aiAnomalyFull_isAKnownKind() {
        assertThat(JobKind.AI_ANOMALY_FULL.wire()).isEqualTo("ai-anomaly-full");
        assertThat(JobKind.fromWire("ai-anomaly-full"))
            .isEqualTo(JobKind.AI_ANOMALY_FULL);
    }

    @Test
    void unknownKind_isRejected() {
        assertThatThrownBy(() -> JobKind.fromWire("telepathy"))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
