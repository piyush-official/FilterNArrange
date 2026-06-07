// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.upload;

import io.filternarrange.gateway.api.upload.dto.UploadResponse;
import io.filternarrange.gateway.application.upload.UploadService;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@RestController
@RequestMapping("/api/v1/upload")
public class UploadController {
    private final UploadService svc;
    public UploadController(UploadService svc) { this.svc = svc; }

    @PostMapping(consumes = "multipart/form-data")
    public UploadResponse upload(@RequestParam("file") MultipartFile file) throws IOException {
        var r = svc.upload(CurrentUser.id(), file);
        return new UploadResponse(r.id(), r.ref(), r.size());
    }
}
