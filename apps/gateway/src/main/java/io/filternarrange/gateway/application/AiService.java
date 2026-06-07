// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application;

import io.filternarrange.gateway.infrastructure.http.DataEngineAiClient;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * Application-layer facade for the four AI capabilities (Plan E §T17). Stays
 * deliberately thin — the orchestrator on the data-engine owns cache, model
 * pinning, and concurrency.
 */
@Service
public class AiService {

    private final DataEngineAiClient client;

    public AiService(DataEngineAiClient client) {
        this.client = client;
    }

    public Map<String, Object> nlToFilter(Map<String, Object> req) {
        return client.nlToFilter(req);
    }

    public Map<String, Object> summary(Map<String, Object> req) {
        return client.summary(req);
    }

    public Map<String, Object> chartSuggest(Map<String, Object> req) {
        return client.chartSuggest(req);
    }

    public Map<String, Object> anomaly(Map<String, Object> req) {
        return client.anomaly(req);
    }
}
