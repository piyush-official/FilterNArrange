// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.analyze.dto;

import java.util.List;
import java.util.Map;

public record AnalyzeResponse(String kind,
                              Map<String, Object> payload,
                              List<String> warnings) {}
