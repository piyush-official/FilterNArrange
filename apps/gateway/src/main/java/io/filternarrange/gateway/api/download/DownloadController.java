// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.download;

import io.filternarrange.gateway.application.download.DownloadService;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/download")
public class DownloadController {

    private final DownloadService svc;
    public DownloadController(DownloadService svc) { this.svc = svc; }

    @GetMapping("/{resultId}")
    public ResponseEntity<Void> download(@PathVariable UUID resultId) {
        String url = svc.presignedUrl(CurrentUser.id(), resultId);
        return ResponseEntity.status(HttpStatus.FOUND).location(URI.create(url)).build();
    }
}
