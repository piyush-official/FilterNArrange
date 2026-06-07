// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.storage;

import io.minio.MinioClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MinioConfig {
    @Bean
    public MinioClient minioClient(
            @Value("${minio.endpoint}") String endpoint,
            @Value("${minio.access-key}") String access,
            @Value("${minio.secret-key}") String secret) {
        return MinioClient.builder().endpoint(endpoint).credentials(access, secret).build();
    }
}
