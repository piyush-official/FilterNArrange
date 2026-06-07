// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "uploads")
public class UploadRecordEntity {
    @Id
    private UUID id;
    @Column(name = "user_id", nullable = false)
    private UUID userId;
    @Column(nullable = false)
    private String ref;
    @Column(name = "size_bytes", nullable = false)
    private long sizeBytes;
    @Column(name = "content_type", nullable = false)
    private String contentType;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public UploadRecordEntity() {}
    public UploadRecordEntity(UUID id, UUID userId, String ref, long sizeBytes, String contentType, Instant createdAt) {
        this.id = id; this.userId = userId; this.ref = ref;
        this.sizeBytes = sizeBytes; this.contentType = contentType; this.createdAt = createdAt;
    }
    public UUID getId() { return id; }
    public UUID getUserId() { return userId; }
    public String getRef() { return ref; }
    public long getSizeBytes() { return sizeBytes; }
    public String getContentType() { return contentType; }
    public Instant getCreatedAt() { return createdAt; }
}
