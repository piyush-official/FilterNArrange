// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.download;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordEntity;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordRepository;
import io.filternarrange.gateway.platform.error.AppException;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class DownloadService {

    private final ResultRecordRepository results;
    private final ObjectStore store;

    public DownloadService(ResultRecordRepository results, ObjectStore store) {
        this.results = results; this.store = store;
    }

    public String presignedUrl(UUID userId, UUID resultId) {
        ResultRecordEntity r = results.findById(resultId)
            .orElseThrow(() -> new AppException("NO_RESULT", 404, "Result not found"));
        if (!r.getUserId().equals(userId))
            throw new AppException("FORBIDDEN", 403, "Not your result");
        String ref = r.getRef();
        int slash = ref.indexOf('/');
        String bucket = ref.substring(0, slash);
        String key = ref.substring(slash + 1);
        return store.presignedGet(bucket, key, 300);
    }
}
