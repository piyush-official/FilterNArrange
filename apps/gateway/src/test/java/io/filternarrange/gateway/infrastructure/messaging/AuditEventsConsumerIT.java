// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import io.filternarrange.gateway.infrastructure.persistence.AuditLogRepository;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.awaitility.Awaitility;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.kafka.test.EmbeddedKafkaBroker;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.time.Duration;
import java.util.Properties;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

/**
 * Plan D §T21 — malformed Kafka messages are dropped silently; the consumer
 * acks them and keeps running. Uses spring-kafka-test's EmbeddedKafkaBroker and
 * overrides the listener auto-startup gate so the consumer beans actually load.
 */
@SpringBootTest(properties = {
    "spring.kafka.listener.auto-startup=true"
})
@EmbeddedKafka(partitions = 1, topics = {
    "topic.v1.jobs",
    "topic.v1.job-results",
    "topic.v1.audit-events",
    "topic.v1.format-requests"
})
@Testcontainers
class AuditEventsConsumerIT {

    @Container
    static PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @Container
    static MinIOContainer MINIO =
        new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        r.add("spring.datasource.username", POSTGRES::getUsername);
        r.add("spring.datasource.password", POSTGRES::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
        r.add("spring.kafka.bootstrap-servers",
              () -> System.getProperty("spring.embedded.kafka.brokers"));
    }

    @MockBean
    private AuditLogRepository repo;

    @Autowired
    private EmbeddedKafkaBroker broker;

    @Test
    void malformedMessageIsDroppedAndConsumerKeepsRunning() throws Exception {
        Properties p = new Properties();
        p.put("bootstrap.servers", broker.getBrokersAsString());
        p.put("key.serializer", StringSerializer.class.getName());
        p.put("value.serializer", StringSerializer.class.getName());
        try (var producer = new KafkaProducer<String, String>(p)) {
            producer.send(new ProducerRecord<>(
                "topic.v1.audit-events", "u", "{\"not\":\"valid\"}")).get();
        }

        // Give the consumer ample time to attempt processing.
        Awaitility.await()
            .pollDelay(Duration.ofSeconds(2))
            .atMost(Duration.ofSeconds(5))
            .untilAsserted(() -> verify(repo, never())
                .insert(any(), anyString(), anyString(), any(), any()));
    }
}
