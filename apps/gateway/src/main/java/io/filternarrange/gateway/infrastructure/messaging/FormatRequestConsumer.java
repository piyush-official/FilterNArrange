// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import io.filternarrange.gateway.infrastructure.github.GithubIssueClient;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.UUID;

/**
 * Plan F §T22 — consumes ``topic.v1.format-requests``, mirrors ``created``
 * events to a GitHub issue, and patches our row with the issue number.
 *
 * Gated on ``spring.kafka.listener.auto-startup=true`` (same pattern as the
 * Plan D consumers) so Spring-test contexts don't pull a broker.
 */
@Component
@ConditionalOnProperty(
    name = "spring.kafka.listener.auto-startup",
    havingValue = "true",
    matchIfMissing = false)
public class FormatRequestConsumer {

    private static final Logger log = LoggerFactory.getLogger(FormatRequestConsumer.class);

    private final ObjectMapper om;
    private final GithubIssueClient github;
    private final FormatRequestRepository repo;

    public FormatRequestConsumer(
        ObjectMapper om,
        GithubIssueClient github,
        FormatRequestRepository repo
    ) {
        this.om = om;
        this.github = github;
        this.repo = repo;
    }

    @KafkaListener(
        topics = KafkaTopics.FORMAT_REQUESTS,
        groupId = "gateway-format-request-mirror",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void onMessage(ConsumerRecord<String, String> rec, Acknowledgment ack) {
        try {
            JsonNode env = om.readTree(rec.value());
            String action = env.path("action").asText("");
            String requestId = env.path("request_id").asText("");
            switch (action) {
                case "created" -> mirrorCreated(env, requestId);
                case "updated" -> mirrorUpdated(env, requestId);
                default -> log.debug("ignoring action={} for request {}", action, requestId);
            }
        } catch (Exception e) {
            log.error("format-request mirror failed at offset {}: {}",
                rec.offset(), e.toString());
        } finally {
            ack.acknowledge();
        }
    }

    private void mirrorCreated(JsonNode env, String requestId) {
        String title = "[format-request] "
            + env.path("user_label").asText("(unlabelled)");
        String body = "Sample ref: " + env.path("sample_ref").asText()
            + "\nRequester: " + env.path("user_id").asText()
            + "\nPriority: " + env.path("priority").asInt(0);
        Integer number = github.createIssue(title, body, List.of("format-request"));
        if (number != null) {
            UUID id = UUID.fromString(requestId);
            repo.updateStatus(id, FormatRequest.Status.TRIAGED, number);
        }
    }

    private void mirrorUpdated(JsonNode env, String requestId) {
        Integer issueNum = env.has("github_issue")
            ? env.path("github_issue").asInt() : null;
        String newStatus = env.path("status").asText("");
        if (issueNum != null && ("shipped".equals(newStatus) || "rejected".equals(newStatus))) {
            github.closeIssue(issueNum, "Status: " + newStatus);
        }
    }
}
