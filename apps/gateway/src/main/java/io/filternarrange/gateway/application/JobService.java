// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobKind;
import io.filternarrange.gateway.domain.job.JobStatus;
import io.filternarrange.gateway.infrastructure.messaging.AuditEventPublisher;
import io.filternarrange.gateway.infrastructure.messaging.JobProducer;
import io.filternarrange.gateway.infrastructure.persistence.JobRepository;
import io.filternarrange.gateway.platform.idempotency.IdempotencyStore;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class JobService {

    private final JobRepository jobs;
    private final JobProducer producer;
    private final AuditEventPublisher audit;
    private final IdempotencyStore idem;
    private final ObjectMapper om;

    public JobService(JobRepository jobs, JobProducer producer,
                      AuditEventPublisher audit, IdempotencyStore idem,
                      ObjectMapper om) {
        this.jobs = jobs;
        this.producer = producer;
        this.audit = audit;
        this.idem = idem;
        this.om = om;
    }

    @Transactional
    public Job submit(UUID userId, String idempotencyKey, String kindWire,
                      JsonNode params, int priority, String traceId)
            throws Exception {

        UUID newJobId = UUID.randomUUID();
        Optional<UUID> existing = idem.putIfAbsent(idempotencyKey, newJobId);
        if (existing.isPresent()) {
            return jobs.findById(existing.get())
                       .orElseThrow(() -> new IllegalStateException(
                           "Idempotency key points to missing job"));
        }

        Job j = new Job(newJobId, userId, JobKind.fromWire(kindWire),
                        JobStatus.QUEUED, params, null, null,
                        priority, Instant.now(), null, null);
        jobs.insert(j);
        producer.publish(j, traceId);

        var meta = om.createObjectNode().put("job_id", j.id().toString());
        audit.publish(userId, "job.submitted", j.id().toString(), meta, traceId);
        return j;
    }

    public Optional<Job> get(UUID jobId) {
        return jobs.findById(jobId);
    }

    public List<Job> recentForUser(UUID userId) {
        return jobs.findRecentByUser(userId, 20);
    }

    @Transactional
    public Job cancel(UUID jobId, String traceId) throws Exception {
        Job j = jobs.findById(jobId)
                    .orElseThrow(() -> new IllegalArgumentException(
                        "Job not found: " + jobId));
        if (j.status().isTerminal()) return j;
        Job cancelled = j.withStatus(JobStatus.CANCELLED);
        jobs.updateStatus(cancelled);
        audit.publish(j.userId(), "job.cancelled", j.id().toString(),
                      null, traceId);
        return cancelled;
    }
}
