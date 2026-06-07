// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.http;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.dataengine.DataEngineClient;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class DataEngineHttpClient implements DataEngineClient {

    private final RestClient rest;
    private final ObjectMapper json;

    public DataEngineHttpClient(RestClient dataEngineRestClient, ObjectMapper json) {
        this.rest = dataEngineRestClient; this.json = json;
    }

    @CircuitBreaker(name = "dataEngine")
    @Override
    public EngineDtos.DetectResult detect(EngineDtos.RefRequest req) {
        return rest.post().uri("/detect").body(req).retrieve().body(EngineDtos.DetectResult.class);
    }

    @CircuitBreaker(name = "dataEngine")
    @Override
    public EngineDtos.FilterResult filter(EngineDtos.FilterRequest req) {
        return rest.post().uri("/filter").body(req).retrieve().body(EngineDtos.FilterResult.class);
    }

    @CircuitBreaker(name = "dataEngine")
    @Override
    public EngineDtos.ConvertResult convert(EngineDtos.ConvertRequest req) {
        return rest.post().uri("/convert").body(req).retrieve().body(EngineDtos.ConvertResult.class);
    }
}
