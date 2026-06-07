// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.error;

public record ErrorEnvelope(String code, String pluginId, String message, String traceId) {
    public static ErrorEnvelope of(String code, String message, String traceId) {
        return new ErrorEnvelope(code, null, message, traceId);
    }
}
