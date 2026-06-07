import * as React from 'react';
import { useJobsList } from '../state/useJobsList';
import { JobProgressCard } from './JobProgressCard';

export function JobsListPage() {
  const { jobs } = useJobsList();
  return (
    <section className="jobs-list">
      <h2>Jobs</h2>
      {jobs.length === 0 ? (
        <p>No jobs yet. Submit one via "Run as job".</p>
      ) : (
        jobs.map((j) => <JobProgressCard key={j.jobId} jobId={j.jobId} />)
      )}
    </section>
  );
}
