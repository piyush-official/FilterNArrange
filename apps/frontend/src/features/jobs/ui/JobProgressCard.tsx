import * as React from 'react';
import { useJob } from '../state/useJob';
import { cancelJob } from '../api/jobsClient';

export interface JobProgressCardProps {
  jobId: string;
}

export function JobProgressCard({ jobId }: JobProgressCardProps) {
  const { job, progress, error } = useJob(jobId);
  if (!job) return <div className="job-card job-card--loading">Loading…</div>;

  const isTerminal = ['completed', 'failed', 'cancelled'].includes(job.status);

  return (
    <div className={`job-card job-card--${job.status}`}>
      <header>
        <span className="job-kind">{job.kind}</span>
        <span className="job-status">{job.status}</span>
      </header>
      <progress value={progress} max={100} />
      {error && (
        <div className="job-error">
          {error.code}: {error.message}
        </div>
      )}
      {!isTerminal && <button onClick={() => cancelJob(jobId)}>Cancel</button>}
      {job.status === 'completed' && job.resultRef && (
        <a
          href={`/api/v1/files/${encodeURIComponent(job.resultRef)}`}
          download
          className="job-download"
        >
          Download result
        </a>
      )}
      {job.status === 'failed' && (
        <a href={`/jobs/${jobId}/error`} className="job-error-link">
          See error
        </a>
      )}
    </div>
  );
}
