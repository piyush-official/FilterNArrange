// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.http;

import java.util.Map;

/** Thrown when data-engine /ai/* returns a non-disabled 4xx/5xx response. */
public class AiUpstreamException extends RuntimeException {

    private final int statusCode;
    private final transient Map<String, Object> detail;

    public AiUpstreamException(int statusCode, Map<String, Object> detail) {
        super(String.valueOf(detail.getOrDefault("message", "")));
        this.statusCode = statusCode;
        this.detail = detail;
    }

    public int statusCode() {
        return statusCode;
    }

    public Map<String, Object> detail() {
        return detail;
    }
}
