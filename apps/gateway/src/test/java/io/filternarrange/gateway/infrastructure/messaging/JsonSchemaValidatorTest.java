// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;


class JsonSchemaValidatorTest {

    private final JsonSchemaValidator v = new JsonSchemaValidator();

    @Test
    void validJobMessagePasses() {
        String msg = "{"
            + "\"job_id\":\"11111111-1111-1111-1111-111111111111\","
            + "\"user_id\":\"22222222-2222-2222-2222-222222222222\","
            + "\"kind\":\"batch-filter\","
            + "\"params\":{\"a\":1},"
            + "\"priority\":0,"
            + "\"created_at\":\"2026-06-07T10:00:00Z\","
            + "\"trace_id\":\"trace-abc\""
            + "}";
        assertThat(v.isValid(KafkaTopics.JOBS, msg)).isTrue();
    }

    @Test
    void jobMessageMissingRequiredFieldFails() {
        String msg = "{"
            + "\"job_id\":\"11111111-1111-1111-1111-111111111111\","
            + "\"kind\":\"batch-filter\","
            + "\"params\":{},"
            + "\"priority\":0,"
            + "\"created_at\":\"2026-06-07T10:00:00Z\","
            + "\"trace_id\":\"trace-abc\""
            + "}";
        assertThatThrownBy(() -> v.validateOrThrow(KafkaTopics.JOBS, msg))
            .hasMessageContaining("user_id");
    }

    @Test
    void validJobResultPasses() {
        String msg = "{"
            + "\"job_id\":\"11111111-1111-1111-1111-111111111111\","
            + "\"status\":\"completed\","
            + "\"result_ref\":\"results/u/x.json\","
            + "\"finished_at\":\"2026-06-07T10:01:00Z\","
            + "\"trace_id\":\"trace-abc\""
            + "}";
        assertThat(v.isValid(KafkaTopics.JOB_RESULTS, msg)).isTrue();
    }

    @Test
    void unknownTopicThrows() {
        assertThatThrownBy(() -> v.validateOrThrow("topic.v1.unknown", "{}"))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
