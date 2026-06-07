// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.upload;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import io.filternarrange.gateway.infrastructure.persistence.UploadRecordEntity;
import io.filternarrange.gateway.infrastructure.persistence.UploadRecordRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.Instant;
import java.util.UUID;

@Service
public class UploadService {

    private final ObjectStore store;
    private final UploadRecordRepository uploads;
    private final String bucket;

    public UploadService(ObjectStore store, UploadRecordRepository uploads,
                         @Value("${minio.buckets.uploads}") String bucket) {
        this.store = store; this.uploads = uploads; this.bucket = bucket;
    }

    public record Uploaded(UUID id, String ref, long size) {}

    public Uploaded upload(UUID userId, MultipartFile file) throws IOException {
        String ext = extensionOf(file.getOriginalFilename());
        UUID id = UUID.randomUUID();
        String key = "users/%s/%s%s".formatted(userId, id, ext);
        store.put(bucket, key, file.getInputStream(), file.getSize(),
            file.getContentType() != null ? file.getContentType() : "application/octet-stream");
        String ref = bucket + "/" + key;
        UploadRecordEntity e = new UploadRecordEntity(id, userId, ref, file.getSize(),
            file.getContentType() != null ? file.getContentType() : "application/octet-stream", Instant.now());
        uploads.save(e);
        return new Uploaded(id, ref, file.getSize());
    }

    public UploadRecordEntity require(UUID id, UUID userId) {
        UploadRecordEntity e = uploads.findById(id).orElseThrow(() ->
            new io.filternarrange.gateway.platform.error.AppException("NO_UPLOAD", 404, "Upload not found"));
        if (!e.getUserId().equals(userId))
            throw new io.filternarrange.gateway.platform.error.AppException("FORBIDDEN", 403, "Not your upload");
        return e;
    }

    private String extensionOf(String name) {
        if (name == null) return "";
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot);
    }
}
