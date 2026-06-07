// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

public final class KafkaTopics {
    public static final String JOBS            = "topic.v1.jobs";
    public static final String JOB_RESULTS     = "topic.v1.job-results";
    public static final String AUDIT_EVENTS    = "topic.v1.audit-events";
    public static final String FORMAT_REQUESTS = "topic.v1.format-requests";

    private KafkaTopics() {}
}
