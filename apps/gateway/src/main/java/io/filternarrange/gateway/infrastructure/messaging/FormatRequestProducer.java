// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

/**
 * Plan F §T19 — emits ``topic.v1.format-requests`` events for the
 * downstream GitHub-issue mirror to consume.
 */
@Component
public class FormatRequestProducer {

    private final KafkaTemplate<String, String> template;
    private final ObjectMapper om;

    public FormatRequestProducer(
        @Qualifier("auditKafkaTemplate") KafkaTemplate<String, String> t,
        ObjectMapper om
    ) {
        this.template = t;
        this.om = om;
    }

    public void publish(FormatRequest fr, String action, String traceId) throws Exception {
        ObjectNode env = om.createObjectNode();
        env.put("request_id", fr.id().toString());
        env.put("user_id",    fr.userId().toString());
        env.put("sample_ref", fr.sampleRef());
        if (fr.userLabel() != null) env.put("user_label", fr.userLabel());
        env.put("status",     fr.status().wire());
        env.put("priority",   fr.priority());
        if (fr.githubIssue() != null) env.put("github_issue", fr.githubIssue());
        env.put("action",     action);
        env.put("trace_id",   traceId);

        String payload = om.writeValueAsString(env);
        template.send(KafkaTopics.FORMAT_REQUESTS, fr.id().toString(), payload)
                .get(10, TimeUnit.SECONDS);
    }
}
