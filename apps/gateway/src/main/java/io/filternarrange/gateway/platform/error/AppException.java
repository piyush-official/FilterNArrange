// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.error;

public class AppException extends RuntimeException {
    private final String code;
    private final int httpStatus;
    public AppException(String code, int httpStatus, String message) {
        super(message); this.code = code; this.httpStatus = httpStatus;
    }
    public String code() { return code; }
    public int httpStatus() { return httpStatus; }
}
