// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Component
public class AuditEventPublisher {

    private final KafkaTemplate<String, String> template;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public AuditEventPublisher(@Qualifier("auditKafkaTemplate") KafkaTemplate<String, String> t,
                               JsonSchemaValidator v, ObjectMapper om) {
        this.template = t;
        this.validator = v;
        this.om = om;
    }

    /** Partition key = user_id (or "system" if null). */
    public void publish(UUID userId, String action, String target,
                        JsonNode metadata, String traceId) throws Exception {
        ObjectNode env = om.createObjectNode();
        env.put("event_id",    UUID.randomUUID().toString());
        if (userId != null) env.put("user_id", userId.toString());
        env.put("action",      action);
        if (target != null) env.put("target", target);
        if (metadata != null) env.set("metadata", metadata);
        env.put("occurred_at", Instant.now().toString());
        env.put("trace_id",    traceId);

        String payload = om.writeValueAsString(env);
        validator.validateOrThrow(KafkaTopics.AUDIT_EVENTS, payload);

        String key = userId == null ? "system" : userId.toString();
        template.send(KafkaTopics.AUDIT_EVENTS, key, payload)
                .get(10, TimeUnit.SECONDS);
    }
}
