// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.ws;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final JobWebSocketHandler handler;

    public WebSocketConfig(JobWebSocketHandler h) {
        this.handler = h;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry r) {
        r.addHandler(handler, "/ws/jobs/*").setAllowedOriginPatterns("*");
    }
}
