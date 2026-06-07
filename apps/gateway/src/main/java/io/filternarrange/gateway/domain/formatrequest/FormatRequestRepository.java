// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.formatrequest;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FormatRequestRepository {
    FormatRequest save(FormatRequest fr);

    Optional<FormatRequest> findById(UUID id);

    List<FormatRequest> listOpen();

    boolean updateStatus(UUID id, FormatRequest.Status next, Integer githubIssue);
}
