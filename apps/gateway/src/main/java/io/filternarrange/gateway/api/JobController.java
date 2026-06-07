// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api;

import io.filternarrange.gateway.api.dto.CreateJobRequest;
import io.filternarrange.gateway.api.dto.JobResponse;
import io.filternarrange.gateway.application.JobService;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import io.filternarrange.gateway.platform.error.AppException;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/jobs")
public class JobController {

    private final JobService jobs;

    public JobController(JobService jobs) {
        this.jobs = jobs;
    }

    @PostMapping
    public ResponseEntity<JobResponse> submit(
            @RequestHeader("Idempotency-Key") String key,
            @RequestHeader(value = "X-Trace-Id", required = false) String traceId,
            @Valid @RequestBody CreateJobRequest req) throws Exception {
        Job j = jobs.submit(
            CurrentUser.id(), key, req.kind(), req.params(),
            req.priority() == null ? 0 : req.priority(),
            traceId == null ? UUID.randomUUID().toString() : traceId);
        return ResponseEntity.accepted().body(toDto(j));
    }

    @GetMapping("/{jobId}")
    public JobResponse get(@PathVariable UUID jobId) {
        return jobs.get(jobId)
                   .map(this::toDto)
                   .orElseThrow(() -> new AppException("NO_JOB", 404, "Job not found"));
    }

    @GetMapping
    public List<JobResponse> recent() {
        return jobs.recentForUser(CurrentUser.id()).stream().map(this::toDto).toList();
    }

    @DeleteMapping("/{jobId}")
    public JobResponse cancel(
            @PathVariable UUID jobId,
            @RequestHeader(value = "X-Trace-Id", required = false) String traceId)
            throws Exception {
        return toDto(jobs.cancel(
            jobId, traceId == null ? UUID.randomUUID().toString() : traceId));
    }

    private JobResponse toDto(Job j) {
        return new JobResponse(
            j.id(), j.status().name().toLowerCase(), j.kind().wire(),
            j.params(), j.resultRef(), j.error(),
            j.createdAt(), j.startedAt(), j.finishedAt());
    }
}
