import { authHeaders, newIdempotencyKey } from '../../../shared/api/client';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Job {
  jobId: string;
  status: JobStatus;
  kind: string;
  params: Record<string, unknown>;
  resultRef?: string;
  error?: { code: string; message: string; pluginId?: string; traceId?: string };
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

export interface CreateJobRequest {
  kind: string;
  params: Record<string, unknown>;
  priority?: number;
}

const BASE = '/api/v1/jobs';

export async function submitJob(req: CreateJobRequest): Promise<Job> {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': newIdempotencyKey(),
      ...authHeaders(),
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`submitJob failed: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/${jobId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`getJob failed: ${res.status}`);
  return res.json();
}

export async function cancelJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/${jobId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`cancelJob failed: ${res.status}`);
  return res.json();
}

export async function listRecentJobs(): Promise<Job[]> {
  const res = await fetch(BASE, { headers: authHeaders() });
  if (!res.ok) throw new Error(`listRecentJobs failed: ${res.status}`);
  return res.json();
}
