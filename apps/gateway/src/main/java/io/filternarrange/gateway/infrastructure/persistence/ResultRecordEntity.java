// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "results")
public class ResultRecordEntity {
    @Id
    private UUID id;
    @Column(name = "user_id", nullable = false)
    private UUID userId;
    @Column(name = "upload_id")
    private UUID uploadId;
    @Column(nullable = false)
    private String ref;
    @Column(name = "output_format", nullable = false)
    private String outputFormat;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public ResultRecordEntity() {}
    public ResultRecordEntity(UUID id, UUID userId, UUID uploadId, String ref, String outputFormat, Instant createdAt) {
        this.id = id; this.userId = userId; this.uploadId = uploadId;
        this.ref = ref; this.outputFormat = outputFormat; this.createdAt = createdAt;
    }
    public UUID getId() { return id; }
    public UUID getUserId() { return userId; }
    public UUID getUploadId() { return uploadId; }
    public String getRef() { return ref; }
    public String getOutputFormat() { return outputFormat; }
    public Instant getCreatedAt() { return createdAt; }
}
