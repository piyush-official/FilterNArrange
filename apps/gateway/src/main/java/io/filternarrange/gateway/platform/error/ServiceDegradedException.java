// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.error;

/**
 * Raised when a downstream component (currently only the data-engine) is in
 * a degraded state — either the Resilience4j breaker is open or a hard
 * dependency is unreachable. Mapped to 503 by {@link GlobalExceptionHandler}
 * in Plan D PR-3.
 */
public class ServiceDegradedException extends RuntimeException {
    private final String code;
    private final String component;

    public ServiceDegradedException(String code, String message, String component) {
        super(message);
        this.code = code;
        this.component = component;
    }

    public String code() { return code; }
    public String component() { return component; }
}
