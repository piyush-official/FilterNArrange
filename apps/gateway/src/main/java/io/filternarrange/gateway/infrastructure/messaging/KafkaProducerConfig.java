// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class KafkaProducerConfig {

    private final String bootstrap;

    public KafkaProducerConfig(@Value("${spring.kafka.bootstrap-servers}") String b) {
        this.bootstrap = b;
    }

    private Map<String, Object> baseProps() {
        Map<String, Object> p = new HashMap<>();
        p.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,             bootstrap);
        p.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,          StringSerializer.class);
        p.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,        StringSerializer.class);
        p.put(ProducerConfig.ACKS_CONFIG,                          "all");
        p.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG,            true);
        p.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);
        p.put(ProducerConfig.RETRIES_CONFIG,                       Integer.MAX_VALUE);
        p.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG,           10_000);   // spec §6
        p.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG,            5_000);
        return p;
    }

    @Bean("jobsProducerFactory")
    public ProducerFactory<String, String> jobsProducerFactory() {
        return new DefaultKafkaProducerFactory<>(baseProps());
    }

    @Bean("jobsKafkaTemplate")
    public KafkaTemplate<String, String> jobsKafkaTemplate() {
        return new KafkaTemplate<>(jobsProducerFactory());
    }

    @Bean("auditProducerFactory")
    public ProducerFactory<String, String> auditProducerFactory() {
        return new DefaultKafkaProducerFactory<>(baseProps());
    }

    @Bean("auditKafkaTemplate")
    public KafkaTemplate<String, String> auditKafkaTemplate() {
        return new KafkaTemplate<>(auditProducerFactory());
    }
}
