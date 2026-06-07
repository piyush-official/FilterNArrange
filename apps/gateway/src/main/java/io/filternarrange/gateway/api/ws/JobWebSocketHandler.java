// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.ws;

import io.filternarrange.gateway.platform.ws.JobSubscriberRegistry;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.UUID;

@Component
public class JobWebSocketHandler extends TextWebSocketHandler {

    private static final String PATH_PREFIX = "/ws/jobs/";

    private final JobSubscriberRegistry registry;

    public JobWebSocketHandler(JobSubscriberRegistry r) {
        this.registry = r;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession s) throws Exception {
        UUID jobId = extract(s);
        if (jobId == null) {
            s.close(CloseStatus.BAD_DATA);
            return;
        }
        registry.register(jobId, s);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession s, CloseStatus status) {
        UUID jobId = extract(s);
        if (jobId != null) registry.unregister(jobId, s);
    }

    private UUID extract(WebSocketSession s) {
        String path = s.getUri() == null ? "" : s.getUri().getPath();
        if (!path.startsWith(PATH_PREFIX)) return null;
        try {
            return UUID.fromString(path.substring(PATH_PREFIX.length()));
        } catch (Exception e) {
            return null;
        }
    }
}
