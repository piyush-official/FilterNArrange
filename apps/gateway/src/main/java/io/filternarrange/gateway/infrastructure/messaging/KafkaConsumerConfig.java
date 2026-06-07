// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.listener.ContainerProperties;

import java.util.HashMap;
import java.util.Map;

/**
 * Active only when spring.kafka.listener.auto-startup=true (compose / k8s
 * deployments set the env var to wake the listeners). Tests inherit the
 * application.yml default of false so the listener beans never load and
 * the gateway Spring context comes up without a broker.
 */
@Configuration
@EnableKafka
@ConditionalOnProperty(
    name = "spring.kafka.listener.auto-startup",
    havingValue = "true",
    matchIfMissing = false)
public class KafkaConsumerConfig {

    private final String bootstrap;

    public KafkaConsumerConfig(@Value("${spring.kafka.bootstrap-servers}") String b) {
        this.bootstrap = b;
    }

    @Bean
    public ConsumerFactory<String, String> consumerFactory() {
        Map<String, Object> p = new HashMap<>();
        p.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,        bootstrap);
        p.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,   StringDeserializer.class);
        p.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        p.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG,       false);
        p.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG,        "earliest");
        return new DefaultKafkaConsumerFactory<>(p);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, String>
            kafkaListenerContainerFactory(ConsumerFactory<String, String> cf) {
        ConcurrentKafkaListenerContainerFactory<String, String> f =
            new ConcurrentKafkaListenerContainerFactory<>();
        f.setConsumerFactory(cf);
        f.getContainerProperties().setAckMode(ContainerProperties.AckMode.MANUAL);
        return f;
    }
}
