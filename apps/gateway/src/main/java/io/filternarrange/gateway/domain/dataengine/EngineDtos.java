// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.dataengine;

import java.util.List;
import java.util.Map;

public final class EngineDtos {
    private EngineDtos() {}

    public record Column(String name, String type, boolean nullable) {}

    public record RefRequest(String ref) {}

    public record ColumnFilterSpec(String kind, List<String> keep) {}

    public record FilterRequest(String ref, ColumnFilterSpec filter, int sampleSize) {}

    public record ConvertRequest(String ref, ColumnFilterSpec filter, String outputFormat) {}

    public record DetectResult(String format, double confidence, List<Column> schema) {}

    public record FilterResult(List<Column> schema, List<Map<String, Object>> rows) {}

    public record ConvertResult(String resultRef) {}
}
