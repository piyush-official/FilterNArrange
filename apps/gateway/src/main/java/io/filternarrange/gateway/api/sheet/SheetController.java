// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.sheet;

import io.filternarrange.gateway.application.pipeline.PipelineService;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1")
public class SheetController {

    private final PipelineService svc;

    public SheetController(PipelineService svc) {
        this.svc = svc;
    }

    @GetMapping("/uploads/{id}/sheets")
    public SheetsResponse sheets(@PathVariable("id") UUID id) {
        List<String> names = svc.listSheets(CurrentUser.id(), id);
        return new SheetsResponse(names);
    }

    public record SheetsResponse(List<String> sheets) {}
}
