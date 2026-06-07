// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

public final class KafkaTopics {
    /** Pre-Plan-F shared topic. Retained as the JSON-schema key for both
     * paid and free variants; physical routing happens via {@link #JOBS_PAID}
     * and {@link #JOBS_FREE}. */
    public static final String JOBS            = "topic.v1.jobs";

    /** Plan F §T17 — tier-routed sub-topics. Schema identical to JOBS. */
    public static final String JOBS_PAID       = "topic.v1.jobs.paid";
    public static final String JOBS_FREE       = "topic.v1.jobs.free";

    public static final String JOB_RESULTS     = "topic.v1.job-results";
    public static final String AUDIT_EVENTS    = "topic.v1.audit-events";
    public static final String FORMAT_REQUESTS = "topic.v1.format-requests";

    private KafkaTopics() {}
}
