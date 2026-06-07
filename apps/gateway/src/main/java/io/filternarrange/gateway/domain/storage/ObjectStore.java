// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.storage;

import java.io.InputStream;

public interface ObjectStore {
    StoredObject put(String bucket, String key, InputStream data, long size, String contentType);
    String presignedGet(String bucket, String key, long expirySeconds);
    boolean exists(String bucket, String key);
    void ensureBucket(String bucket);
}
