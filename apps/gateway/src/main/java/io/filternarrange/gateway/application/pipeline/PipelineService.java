// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.pipeline;

import io.filternarrange.gateway.application.upload.UploadService;
import io.filternarrange.gateway.domain.dataengine.DataEngineClient;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordEntity;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordRepository;
import io.filternarrange.gateway.infrastructure.persistence.UploadRecordEntity;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class PipelineService {

    private final UploadService uploads;
    private final DataEngineClient engine;
    private final ResultRecordRepository results;

    public PipelineService(UploadService uploads, DataEngineClient engine, ResultRecordRepository results) {
        this.uploads = uploads; this.engine = engine; this.results = results;
    }

    public EngineDtos.DetectResult detect(UUID userId, UUID uploadId) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        return engine.detect(new EngineDtos.RefRequest(u.getRef()));
    }

    /**
     * Plan C: filter shape is a passthrough map so the gateway accepts
     * column / row / expression / regex specs without code changes.
     */
    public EngineDtos.FilterResult filterPreview(UUID userId, UUID uploadId,
                                                 Map<String, Object> filter, int sampleSize) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        return engine.preview(new EngineDtos.PreviewRequest(u.getRef(), filter, sampleSize));
    }

    public record Converted(UUID resultId, String ref) {}

    public Converted convert(UUID userId, UUID uploadId, List<String> keep, String outputFormat) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        EngineDtos.ConvertResult r = engine.convert(new EngineDtos.ConvertRequest(
            u.getRef(),
            new EngineDtos.ColumnFilterSpec("column", keep),
            outputFormat));
        UUID id = UUID.randomUUID();
        results.save(new ResultRecordEntity(id, userId, u.getId(), r.resultRef(), outputFormat, Instant.now()));
        return new Converted(id, r.resultRef());
    }

    public EngineDtos.AnalyzeResult analyze(UUID userId, UUID uploadId,
                                            Map<String, Object> analysis,
                                            Map<String, Object> filter) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        return engine.analyze(new EngineDtos.AnalyzeRequest(u.getRef(), analysis, filter));
    }

    public List<String> listSheets(UUID userId, UUID uploadId) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        return engine.sheets(new EngineDtos.SheetsRequest(u.getRef())).sheets();
    }
}
