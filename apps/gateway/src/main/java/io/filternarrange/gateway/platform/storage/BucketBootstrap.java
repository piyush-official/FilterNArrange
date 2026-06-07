// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.storage;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class BucketBootstrap {

    private final ObjectStore store;
    private final String uploads;
    private final String results;
    private final String samples;
    private final String backups;

    public BucketBootstrap(ObjectStore store,
                           @Value("${minio.buckets.uploads}") String uploads,
                           @Value("${minio.buckets.results}") String results,
                           @Value("${minio.buckets.format-samples}") String samples,
                           @Value("${minio.buckets.backups}") String backups) {
        this.store = store; this.uploads = uploads; this.results = results;
        this.samples = samples; this.backups = backups;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void bootstrap() {
        for (String b : new String[]{uploads, results, samples, backups}) store.ensureBucket(b);
    }
}
