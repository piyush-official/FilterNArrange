// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.api.ws.JobSubscriberRegistry;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobStatus;
import io.filternarrange.gateway.infrastructure.persistence.JobRepository;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

import java.util.UUID;

@Component
public class JobResultsConsumer {

    private static final Logger log = LoggerFactory.getLogger(JobResultsConsumer.class);

    private final JobRepository jobs;
    private final JobSubscriberRegistry subs;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public JobResultsConsumer(JobRepository jobs, JobSubscriberRegistry subs,
                              JsonSchemaValidator v, ObjectMapper om) {
        this.jobs = jobs;
        this.subs = subs;
        this.validator = v;
        this.om = om;
    }

    @KafkaListener(topics = KafkaTopics.JOB_RESULTS,
                   groupId = "gateway-job-results",
                   containerFactory = "kafkaListenerContainerFactory")
    public void onMessage(ConsumerRecord<String, String> rec, Acknowledgment ack) {
        try {
            validator.validateOrThrow(KafkaTopics.JOB_RESULTS, rec.value());
            JsonNode n = om.readTree(rec.value());
            UUID jobId = UUID.fromString(n.get("job_id").asText());
            JobStatus status = JobStatus.valueOf(n.get("status").asText().toUpperCase());

            jobs.findById(jobId).ifPresent(j -> {
                if (j.status() == status) {
                    // heartbeat retransmission — fan out only
                } else if (j.status().canTransitionTo(status)) {
                    Job updated = j.withStatus(status);
                    String resultRef = n.hasNonNull("result_ref") ? n.get("result_ref").asText() : updated.resultRef();
                    JsonNode error = n.hasNonNull("error") ? n.get("error") : updated.error();
                    updated = updated.withResult(resultRef, error);
                    jobs.updateStatus(updated);
                } else {
                    log.warn("Invalid transition {} -> {} for job {}",
                             j.status(), status, jobId);
                    return;
                }
                subs.broadcast(jobId, rec.value(), status.isTerminal());
            });
            ack.acknowledge();
        } catch (Exception e) {
            log.error("Rejecting malformed job-result message at offset {}: {}",
                      rec.offset(), e.getMessage());
            ack.acknowledge();
        }
    }
}
