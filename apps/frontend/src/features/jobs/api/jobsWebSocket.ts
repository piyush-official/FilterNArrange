import type { JobStatus } from './jobsClient';

export interface JobResultEnvelope {
  job_id: string;
  status: JobStatus;
  progress?: number;
  result_ref?: string;
  error?: { code: string; message: string; plugin_id?: string; trace_id?: string };
  finished_at: string;
  trace_id: string;
}

export type JobResultListener = (env: JobResultEnvelope) => void;

export function openJobSocket(
  jobId: string,
  onEvent: JobResultListener,
  onClose?: () => void,
): () => void {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws/jobs/${jobId}`);

  ws.addEventListener('message', (evt: MessageEvent) => {
    try {
      onEvent(JSON.parse(evt.data) as JobResultEnvelope);
    } catch (e) {
      console.error('Bad job-result envelope', e);
    }
  });
  ws.addEventListener('close', () => onClose?.());

  return () => ws.close();
}
