// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.storage;

public record StoredObject(String bucket, String key, long sizeBytes, String contentType) {}
