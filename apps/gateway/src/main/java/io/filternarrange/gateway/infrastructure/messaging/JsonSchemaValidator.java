// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SchemaValidatorsConfig;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Validates Kafka messages against the JSON schemas shipped in
 * {@code contracts/kafka/*.schema.json}. The schemas land on the runtime
 * classpath via the {@code sourceSets.main.resources.srcDir(rootProject.file("contracts"))}
 * hook in {@code build.gradle.kts} — that strips the {@code contracts/} prefix,
 * so on the classpath the files live at {@code /kafka/...}.
 *
 * Uses {@code networknt/json-schema-validator} so we get draft-2019-09 +
 * draft-2020-12 support natively. {@code everit-json-schema} only goes up
 * to draft-07 and silently failed on these schemas.
 */
@Component
public class JsonSchemaValidator {

    private static final Map<String, String> SCHEMA_PATHS = Map.of(
        KafkaTopics.JOBS,            "/kafka/topic.v1.jobs.schema.json",
        KafkaTopics.JOB_RESULTS,     "/kafka/topic.v1.job-results.schema.json",
        KafkaTopics.AUDIT_EVENTS,    "/kafka/topic.v1.audit-events.schema.json",
        KafkaTopics.FORMAT_REQUESTS, "/kafka/topic.v1.format-requests.schema.json"
    );

    private final JsonSchemaFactory factory =
        JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V201909);
    private final SchemaValidatorsConfig config = new SchemaValidatorsConfig();
    private final ObjectMapper om = new ObjectMapper();
    private final Map<String, JsonSchema> cache = new ConcurrentHashMap<>();

    public boolean isValid(String topic, String json) {
        try {
            validateOrThrow(topic, json);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public void validateOrThrow(String topic, String json) {
        JsonSchema schema = cache.computeIfAbsent(topic, this::load);
        JsonNode node;
        try {
            node = om.readTree(json);
        } catch (Exception e) {
            throw new IllegalArgumentException("Malformed JSON: " + e.getMessage(), e);
        }
        Set<ValidationMessage> errors = schema.validate(node);
        if (!errors.isEmpty()) {
            String summary = errors.stream()
                .map(ValidationMessage::getMessage)
                .collect(Collectors.joining("; "));
            throw new IllegalArgumentException(summary);
        }
    }

    private JsonSchema load(String topic) {
        String path = SCHEMA_PATHS.get(topic);
        if (path == null) {
            throw new IllegalArgumentException("Unknown topic: " + topic);
        }
        try (InputStream in = JsonSchemaValidator.class.getResourceAsStream(path)) {
            if (in == null) {
                throw new IllegalStateException("Schema not on classpath: " + path);
            }
            return factory.getSchema(in, config);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load schema " + path, e);
        }
    }
}
