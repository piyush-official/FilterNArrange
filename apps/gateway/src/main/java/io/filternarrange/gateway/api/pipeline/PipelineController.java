// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.pipeline;

import io.filternarrange.gateway.api.pipeline.dto.*;
import io.filternarrange.gateway.application.pipeline.PipelineService;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class PipelineController {

    private final PipelineService svc;
    public PipelineController(PipelineService svc) { this.svc = svc; }

    @PostMapping("/detect")
    public EngineDtos.DetectResult detect(@Valid @RequestBody DetectRequest r) {
        return svc.detect(CurrentUser.id(), r.uploadId());
    }

    @PostMapping("/filter/preview")
    public EngineDtos.FilterResult preview(@Valid @RequestBody FilterPreviewRequest r) {
        int n = r.sampleSize() == null ? 20 : r.sampleSize();
        return svc.filterPreview(CurrentUser.id(), r.uploadId(), r.filter().keep(), n);
    }

    @PostMapping("/convert")
    public ConvertResponse convert(@Valid @RequestBody ConvertRequest r) {
        var c = svc.convert(CurrentUser.id(), r.uploadId(), r.filter().keep(), r.outputFormat());
        return new ConvertResponse(c.resultId(), c.ref());
    }
}
