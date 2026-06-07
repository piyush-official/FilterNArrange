// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.threads;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

@Configuration
public class ThreadPoolConfig {

    /** Bulkhead for Kafka producer sends — spec §6. */
    @Bean(name = "kafkaProducerExecutor")
    public ThreadPoolTaskExecutor kafkaProducerExecutor() {
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(4);
        e.setMaxPoolSize(4);
        e.setQueueCapacity(256);
        e.setThreadNamePrefix("kafka-producer-");
        e.initialize();
        return e;
    }
}
