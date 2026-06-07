// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.http;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {
    @Bean
    public RestClient dataEngineRestClient(
            @Value("${data-engine.base-url}") String baseUrl,
            @Value("${data-engine.connect-timeout-ms}") int connectTimeout,
            @Value("${data-engine.read-timeout-ms}") int readTimeout) {
        var f = new SimpleClientHttpRequestFactory();
        f.setConnectTimeout(connectTimeout);
        f.setReadTimeout(readTimeout);
        return RestClient.builder().baseUrl(baseUrl).requestFactory(f).build();
    }
}
