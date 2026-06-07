import { useEffect, useState } from 'react';
import { type Job, listRecentJobs } from '../api/jobsClient';

export function useJobsList(): { jobs: Job[]; refresh: () => Promise<void> } {
  const [jobs, setJobs] = useState<Job[]>([]);
  const refresh = async () => setJobs(await listRecentJobs());
  useEffect(() => {
    refresh().catch(() => {});
  }, []);
  return { jobs, refresh };
}
