import { useEffect, useState } from 'react';
import { type Job, getJob } from '../api/jobsClient';
import { openJobSocket } from '../api/jobsWebSocket';

export interface UseJobResult {
  job: Job | undefined;
  progress: number;
  error: { code: string; message: string } | undefined;
}

export function useJob(jobId: string | undefined): UseJobResult {
  const [job, setJob] = useState<Job | undefined>(undefined);
  const [progress, setProgress] = useState(0);
  const [error, setError] =
    useState<{ code: string; message: string } | undefined>();

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    getJob(jobId)
      .then((j) => {
        if (!cancelled) setJob(j);
      })
      .catch(() => {});

    const close = openJobSocket(jobId, (env) => {
      setJob((prev) => ({
        ...(prev ?? {
          jobId: env.job_id,
          kind: '',
          params: {},
          createdAt: env.finished_at,
        } as Job),
        status: env.status,
        resultRef: env.result_ref ?? prev?.resultRef,
        error: env.error
          ? {
              code: env.error.code,
              message: env.error.message,
              pluginId: env.error.plugin_id,
              traceId: env.error.trace_id,
            }
          : prev?.error,
        finishedAt: env.finished_at,
      }));
      if (typeof env.progress === 'number') setProgress(env.progress);
      if (env.error) setError({ code: env.error.code, message: env.error.message });
    });

    return () => {
      cancelled = true;
      close();
    };
  }, [jobId]);

  return { job, progress, error };
}
