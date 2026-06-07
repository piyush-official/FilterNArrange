// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.storage;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import io.filternarrange.gateway.domain.storage.StoredObject;
import io.minio.*;
import io.minio.http.Method;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.concurrent.TimeUnit;

@Component
public class MinioObjectStore implements ObjectStore {

    private final MinioClient client;
    public MinioObjectStore(MinioClient client) { this.client = client; }

    @Override
    public StoredObject put(String bucket, String key, InputStream data, long size, String contentType) {
        try {
            ensureBucket(bucket);
            client.putObject(PutObjectArgs.builder()
                .bucket(bucket).object(key)
                .stream(data, size, -1)
                .contentType(contentType)
                .build());
            return new StoredObject(bucket, key, size, contentType);
        } catch (Exception e) {
            throw new RuntimeException("minio put failed: " + e.getMessage(), e);
        }
    }

    @Override
    public String presignedGet(String bucket, String key, long expirySeconds) {
        try {
            return client.getPresignedObjectUrl(GetPresignedObjectUrlArgs.builder()
                .method(Method.GET).bucket(bucket).object(key)
                .expiry((int) expirySeconds, TimeUnit.SECONDS)
                .build());
        } catch (Exception e) {
            throw new RuntimeException("minio presign failed: " + e.getMessage(), e);
        }
    }

    @Override
    public boolean exists(String bucket, String key) {
        try {
            client.statObject(StatObjectArgs.builder().bucket(bucket).object(key).build());
            return true;
        } catch (Exception e) { return false; }
    }

    @Override
    public void ensureBucket(String bucket) {
        try {
            boolean found = client.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
            if (!found) client.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
        } catch (Exception e) {
            throw new RuntimeException("minio ensure bucket: " + e.getMessage(), e);
        }
    }
}
