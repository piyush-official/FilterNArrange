// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.http;

import java.util.Map;

/** Thrown when data-engine returns 404 with code=AI_CAPABILITY_DISABLED. */
public class AiCapabilityDisabledException extends RuntimeException {

    private final transient Map<String, Object> detail;

    public AiCapabilityDisabledException(Map<String, Object> detail) {
        super(String.valueOf(detail.getOrDefault("message", "")));
        this.detail = detail;
    }

    public Map<String, Object> detail() {
        return detail;
    }
}
