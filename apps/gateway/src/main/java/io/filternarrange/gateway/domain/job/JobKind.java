// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.job;

public enum JobKind {
    BATCH_FILTER("batch-filter"),
    CONVERT("convert"),
    ANALYZE("analyze");

    private final String wire;

    JobKind(String wire) { this.wire = wire; }

    public String wire() { return wire; }

    public static JobKind fromWire(String s) {
        for (var k : values()) {
            if (k.wire.equals(s)) return k;
        }
        throw new IllegalArgumentException("Unknown job kind: " + s);
    }
}
