// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.ws;

import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Tracks the in-flight WebSocket sessions per job-id. Plan D §3 fan-out.
 * Thread-safe; sessions are added on connect and removed on disconnect or
 * when {@link #broadcast(UUID, String, boolean)} is invoked with
 * {@code closeAfter=true} (terminal status events).
 */
@Component
public class JobSubscriberRegistry {

    private final Map<UUID, Set<WebSocketSession>> sessionsByJob = new ConcurrentHashMap<>();

    public void register(UUID jobId, WebSocketSession s) {
        sessionsByJob.computeIfAbsent(jobId, k -> ConcurrentHashMap.newKeySet()).add(s);
    }

    public void unregister(UUID jobId, WebSocketSession s) {
        Set<WebSocketSession> set = sessionsByJob.get(jobId);
        if (set != null) {
            set.remove(s);
            if (set.isEmpty()) sessionsByJob.remove(jobId);
        }
    }

    public void broadcast(UUID jobId, String payload, boolean closeAfter) {
        Set<WebSocketSession> set = sessionsByJob.get(jobId);
        if (set == null) return;
        for (WebSocketSession s : set) {
            try {
                if (s.isOpen()) {
                    s.sendMessage(new TextMessage(payload));
                }
                if (closeAfter && s.isOpen()) {
                    s.close();
                }
            } catch (IOException ignored) {
                // Closed/broken sessions get cleaned up on the next register/unregister cycle.
            }
        }
        if (closeAfter) sessionsByJob.remove(jobId);
    }
}
