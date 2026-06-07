// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.filternarrange.gateway.platform.tier.TierResolver;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class JobProducer {

    private final KafkaTemplate<String, String> template;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;
    private final TierResolver tierResolver;

    public JobProducer(
        @Qualifier("jobsKafkaTemplate") KafkaTemplate<String, String> t,
        JsonSchemaValidator v,
        ObjectMapper om,
        TierResolver tierResolver
    ) {
        this.template = t;
        this.validator = v;
        this.om = om;
        this.tierResolver = tierResolver;
    }

    /**
     * Partition key = user_id, per spec §5. Blocks up to 10s — spec §6.
     * Routes to ``topic.v1.jobs.paid`` or ``topic.v1.jobs.free`` based on the
     * submitter's tier (Plan F §T17). Schema is validated under the shared
     * ``topic.v1.jobs`` key.
     */
    public void publish(Job j, String traceId) throws Exception {
        ObjectNode env = om.createObjectNode();
        env.put("job_id",     j.id().toString());
        env.put("user_id",    j.userId().toString());
        env.put("kind",       j.kind().wire());
        env.set ("params",    j.params());
        env.put("priority",   j.priority());
        env.put("created_at", j.createdAt().toString());
        env.put("trace_id",   traceId);

        String payload = om.writeValueAsString(env);
        validator.validateOrThrow(KafkaTopics.JOBS, payload);

        Tier tier = tierResolver.resolve(j.userId());
        String topic = tier == Tier.PAID ? KafkaTopics.JOBS_PAID : KafkaTopics.JOBS_FREE;
        template.send(topic, j.userId().toString(), payload)
                .get(10, TimeUnit.SECONDS);
    }
}
