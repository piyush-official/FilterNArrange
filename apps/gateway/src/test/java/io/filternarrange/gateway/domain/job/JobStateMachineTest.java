// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.job;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;


class JobStateMachineTest {

    @Test
    void queuedCanTransitionToRunningOrCancelled() {
        assertThat(JobStatus.QUEUED.canTransitionTo(JobStatus.RUNNING)).isTrue();
        assertThat(JobStatus.QUEUED.canTransitionTo(JobStatus.CANCELLED)).isTrue();
        assertThat(JobStatus.QUEUED.canTransitionTo(JobStatus.COMPLETED)).isFalse();
    }

    @Test
    void terminalStatesAreTerminal() {
        assertThat(JobStatus.COMPLETED.isTerminal()).isTrue();
        assertThat(JobStatus.FAILED.isTerminal()).isTrue();
        assertThat(JobStatus.CANCELLED.isTerminal()).isTrue();
        assertThat(JobStatus.QUEUED.isTerminal()).isFalse();
        assertThat(JobStatus.RUNNING.isTerminal()).isFalse();
    }

    @Test
    void invalidTransitionThrows() {
        var j = new io.filternarrange.gateway.domain.job.Job(
            java.util.UUID.randomUUID(), java.util.UUID.randomUUID(),
            JobKind.BATCH_FILTER, JobStatus.COMPLETED, null, null, null, 0,
            java.time.Instant.now(), null, null);
        assertThatThrownBy(() -> j.withStatus(JobStatus.RUNNING))
            .isInstanceOf(IllegalStateException.class)
            .hasMessageContaining("Invalid transition");
    }

    @Test
    void jobKindRoundtripsThroughWire() {
        for (JobKind k : JobKind.values()) {
            assertThat(JobKind.fromWire(k.wire())).isEqualTo(k);
        }
    }
}
