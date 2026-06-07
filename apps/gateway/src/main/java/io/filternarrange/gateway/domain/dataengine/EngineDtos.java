// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.dataengine;

import java.util.List;
import java.util.Map;

public final class EngineDtos {
    private EngineDtos() {}

    public record Column(String name, String type, boolean nullable) {}

    public record RefRequest(String ref) {}

    public record ColumnFilterSpec(String kind, List<String> keep) {}

    /**
     * Generic filter payload that accepts column / row / expression / regex
     * shapes (Plan C). The data-engine validates the kind + fields.
     */
    public record PreviewRequest(String ref, Map<String, Object> filter, int sampleSize) {}

    /**
     * Plan B's typed convert call. The data-engine /convert route still
     * accepts the typed ColumnFilterSpec for the column-only path.
     */
    public record ConvertRequest(String ref, ColumnFilterSpec filter, String outputFormat) {}

    public record DetectResult(String format, double confidence, List<Column> schema) {}

    public record FilterResult(List<Column> schema, List<Map<String, Object>> rows) {}

    public record ConvertResult(String resultRef) {}

    // ---- Plan C additions --------------------------------------------------

    public record AnalyzeRequest(String ref,
                                 Map<String, Object> analysis,
                                 Map<String, Object> filter) {}

    public record AnalyzeResult(String kind,
                                Map<String, Object> payload,
                                List<String> warnings) {}

    public record SheetsRequest(String ref) {}

    public record SheetsResult(List<String> sheets) {}
}
