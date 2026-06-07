// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.http;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class DataEngineHttpClientTest {

    DataEngineHttpClient client;
    MockRestServiceServer server;
    ObjectMapper json = new ObjectMapper();

    @BeforeEach
    void setup() {
        var builder = RestClient.builder().baseUrl("http://data-engine:8000");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new DataEngineHttpClient(builder.build(), json);
    }

    @Test
    void detect_callsEngine() throws Exception {
        server.expect(requestTo("http://data-engine:8000/detect"))
            .andExpect(content().contentType(MediaType.APPLICATION_JSON))
            .andRespond(withSuccess("""
                {"format":"csv","confidence":0.97,"schema":[{"name":"a","type":"string","nullable":false}]}
                """, MediaType.APPLICATION_JSON));
        var res = client.detect(new EngineDtos.RefRequest("uploads/u/abc.csv"));
        assertThat(res.format()).isEqualTo("csv");
        assertThat(res.confidence()).isEqualTo(0.97);
        assertThat(res.schema()).hasSize(1);
    }

    @Test
    void preview_callsEngine() {
        server.expect(requestTo("http://data-engine:8000/filter"))
            .andRespond(withSuccess("""
                {"schema":[{"name":"a","type":"string","nullable":false}],"rows":[{"a":"1"}]}
                """, MediaType.APPLICATION_JSON));
        var res = client.preview(new EngineDtos.PreviewRequest(
            "uploads/u/abc.csv",
            Map.of("kind", "column", "keep", List.of("a")),
            20));
        assertThat(res.rows()).hasSize(1);
        assertThat(res.rows().get(0)).containsEntry("a", "1");
    }
}
