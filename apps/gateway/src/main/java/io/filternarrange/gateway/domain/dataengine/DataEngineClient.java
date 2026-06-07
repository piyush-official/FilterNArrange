// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.dataengine;

public interface DataEngineClient {
    EngineDtos.DetectResult detect(EngineDtos.RefRequest req);
    EngineDtos.FilterResult preview(EngineDtos.PreviewRequest req);
    EngineDtos.ConvertResult convert(EngineDtos.ConvertRequest req);
    EngineDtos.AnalyzeResult analyze(EngineDtos.AnalyzeRequest req);
    EngineDtos.SheetsResult sheets(EngineDtos.SheetsRequest req);
}
