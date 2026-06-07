// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.job;

import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

public enum JobStatus {
    QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED;

    private static final Map<JobStatus, Set<JobStatus>> TRANSITIONS = Map.of(
        QUEUED,    EnumSet.of(RUNNING, CANCELLED, FAILED),
        RUNNING,   EnumSet.of(COMPLETED, FAILED, CANCELLED),
        COMPLETED, EnumSet.noneOf(JobStatus.class),
        FAILED,    EnumSet.noneOf(JobStatus.class),
        CANCELLED, EnumSet.noneOf(JobStatus.class)
    );

    public boolean canTransitionTo(JobStatus next) {
        return TRANSITIONS.get(this).contains(next);
    }

    public boolean isTerminal() {
        return TRANSITIONS.get(this).isEmpty();
    }
}
