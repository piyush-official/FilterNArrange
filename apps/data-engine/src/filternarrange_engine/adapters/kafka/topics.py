"""Topic name constants — kept in lock-step with KafkaTopics.java in the gateway."""
from __future__ import annotations

JOBS = "topic.v1.jobs"
JOB_RESULTS = "topic.v1.job-results"
AUDIT_EVENTS = "topic.v1.audit-events"
FORMAT_REQUESTS = "topic.v1.format-requests"

ALL_TOPICS = (JOBS, JOB_RESULTS, AUDIT_EVENTS, FORMAT_REQUESTS)
