// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.analyze;

import io.filternarrange.gateway.api.analyze.dto.AnalyzeRequest;
import io.filternarrange.gateway.api.analyze.dto.AnalyzeResponse;
import io.filternarrange.gateway.application.pipeline.PipelineService;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class AnalyzeController {

    private final PipelineService svc;

    public AnalyzeController(PipelineService svc) {
        this.svc = svc;
    }

    @PostMapping("/analyze")
    public AnalyzeResponse analyze(@Valid @RequestBody AnalyzeRequest req) {
        EngineDtos.AnalyzeResult r = svc.analyze(CurrentUser.id(), req.uploadId(), req.analysis(), req.filter());
        return new AnalyzeResponse(r.kind(), r.payload(), r.warnings());
    }
}
