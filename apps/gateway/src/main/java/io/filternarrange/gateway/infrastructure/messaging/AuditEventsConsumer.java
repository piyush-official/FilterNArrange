// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.infrastructure.persistence.AuditLogRepository;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.UUID;

@Component
public class AuditEventsConsumer {

    private static final Logger log = LoggerFactory.getLogger(AuditEventsConsumer.class);

    private final AuditLogRepository repo;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public AuditEventsConsumer(AuditLogRepository repo,
                               JsonSchemaValidator v, ObjectMapper om) {
        this.repo = repo;
        this.validator = v;
        this.om = om;
    }

    @KafkaListener(topics = KafkaTopics.AUDIT_EVENTS,
                   groupId = "gateway-audit-writer",
                   containerFactory = "kafkaListenerContainerFactory")
    public void onMessage(ConsumerRecord<String, String> rec, Acknowledgment ack) {
        try {
            validator.validateOrThrow(KafkaTopics.AUDIT_EVENTS, rec.value());
            JsonNode n = om.readTree(rec.value());
            UUID userId = n.hasNonNull("user_id")
                ? UUID.fromString(n.get("user_id").asText()) : null;
            String action = n.get("action").asText();
            String target = n.hasNonNull("target") ? n.get("target").asText() : null;
            JsonNode meta = n.hasNonNull("metadata") ? n.get("metadata") : null;
            Instant occurredAt = Instant.parse(n.get("occurred_at").asText());
            repo.insert(userId, action, target, meta, occurredAt);
            ack.acknowledge();
        } catch (Exception e) {
            log.error("Audit-event rejected at offset {}: {}",
                      rec.offset(), e.getMessage());
            ack.acknowledge();
        }
    }
}
