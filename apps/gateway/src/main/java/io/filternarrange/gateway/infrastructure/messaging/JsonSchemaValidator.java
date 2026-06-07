// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import org.everit.json.schema.Schema;
import org.everit.json.schema.loader.SchemaLoader;
import org.json.JSONObject;
import org.json.JSONTokener;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Validates Kafka messages against the JSON schemas shipped in
 * {@code contracts/kafka/*.schema.json}. The schemas land on the runtime
 * classpath via the {@code sourceSets.main.resources.srcDir(rootProject.file("contracts"))}
 * hook in {@code build.gradle.kts} — that strips the {@code contracts/} prefix,
 * so on the classpath the files live at {@code /kafka/...}.
 */
@Component
public class JsonSchemaValidator {

    private static final Map<String, String> SCHEMA_PATHS = Map.of(
        KafkaTopics.JOBS,            "/kafka/topic.v1.jobs.schema.json",
        KafkaTopics.JOB_RESULTS,     "/kafka/topic.v1.job-results.schema.json",
        KafkaTopics.AUDIT_EVENTS,    "/kafka/topic.v1.audit-events.schema.json",
        KafkaTopics.FORMAT_REQUESTS, "/kafka/topic.v1.format-requests.schema.json"
    );

    private final Map<String, Schema> cache = new ConcurrentHashMap<>();

    public boolean isValid(String topic, String json) {
        try {
            validateOrThrow(topic, json);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public void validateOrThrow(String topic, String json) {
        Schema schema = cache.computeIfAbsent(topic, this::load);
        schema.validate(new JSONObject(new JSONTokener(json)));
    }

    private Schema load(String topic) {
        String path = SCHEMA_PATHS.get(topic);
        if (path == null) {
            throw new IllegalArgumentException("Unknown topic: " + topic);
        }
        try (InputStream in = JsonSchemaValidator.class.getResourceAsStream(path)) {
            if (in == null) {
                throw new IllegalStateException("Schema not on classpath: " + path);
            }
            return SchemaLoader.load(new JSONObject(new JSONTokener(in)));
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load schema " + path, e);
        }
    }
}
