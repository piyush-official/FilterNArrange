// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.formatrequest;

import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import io.filternarrange.gateway.infrastructure.messaging.FormatRequestProducer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Plan F §T19/T23 — submit + admin-side transition flow for format requests.
 * Submit emits a ``created`` Kafka event; admin transitions emit ``updated``.
 */
@Service
public class FormatRequestService {

    private static final Logger log = LoggerFactory.getLogger(FormatRequestService.class);

    private final FormatRequestRepository repo;
    private final FormatRequestProducer producer;

    public FormatRequestService(FormatRequestRepository repo, FormatRequestProducer producer) {
        this.repo = repo;
        this.producer = producer;
    }

    public FormatRequest submit(UUID userId, String sampleRef, String userLabel) {
        FormatRequest fr = new FormatRequest(
            UUID.randomUUID(),
            userId,
            sampleRef,
            userLabel,
            FormatRequest.Status.OPEN,
            0,
            null,
            Instant.now(),
            null
        );
        FormatRequest saved = repo.save(fr);
        tryEmit(saved, "created");
        return saved;
    }

    public List<FormatRequest> listOpen() {
        return repo.listOpen();
    }

    public Optional<FormatRequest> transition(
        UUID id, FormatRequest.Status next, Integer githubIssue
    ) {
        if (!repo.updateStatus(id, next, githubIssue)) {
            return Optional.empty();
        }
        Optional<FormatRequest> updated = repo.findById(id);
        updated.ifPresent(fr -> tryEmit(fr, "updated"));
        return updated;
    }

    public Optional<FormatRequest> get(UUID id) {
        return repo.findById(id);
    }

    private void tryEmit(FormatRequest fr, String action) {
        try {
            producer.publish(fr, action, UUID.randomUUID().toString());
        } catch (Exception e) {
            log.warn(
                "format-request kafka emit failed (id={}, action={}): {}",
                fr.id(), action, e.toString()
            );
        }
    }
}
