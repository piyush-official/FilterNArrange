// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.filternarrange.gateway.domain.job.Job;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class JobProducer {

    private final KafkaTemplate<String, String> template;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public JobProducer(@Qualifier("jobsKafkaTemplate") KafkaTemplate<String, String> t,
                       JsonSchemaValidator v,
                       ObjectMapper om) {
        this.template = t;
        this.validator = v;
        this.om = om;
    }

    /** Partition key = user_id, per spec §5. Blocks up to 10s — spec §6. */
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

        template.send(KafkaTopics.JOBS, j.userId().toString(), payload)
                .get(10, TimeUnit.SECONDS);
    }
}
