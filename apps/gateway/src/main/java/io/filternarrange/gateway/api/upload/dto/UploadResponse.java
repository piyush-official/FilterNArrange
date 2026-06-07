// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.upload.dto;

import java.util.UUID;
public record UploadResponse(UUID uploadId, String ref, long sizeBytes) {}
