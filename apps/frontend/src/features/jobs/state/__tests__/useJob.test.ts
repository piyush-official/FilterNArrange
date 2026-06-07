import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useJob } from '../useJob';

vi.mock('../../api/jobsClient', () => ({
  getJob: vi.fn().mockResolvedValue({
    jobId: 'j-1',
    status: 'queued',
    kind: 'batch-filter',
    params: {},
    createdAt: '2026-06-07T00:00:00Z',
  }),
}));

vi.mock('../../api/jobsWebSocket', () => ({
  openJobSocket: (id: string, on: (e: unknown) => void) => {
    setTimeout(
      () =>
        on({
          job_id: id,
          status: 'completed',
          progress: 100,
          result_ref: 'results/abc',
          finished_at: '2026-06-07T00:01:00Z',
          trace_id: 't',
        }),
      10,
    );
    return () => {};
  },
}));

describe('useJob', () => {
  it('transitions queued → completed over WS', async () => {
    const { result } = renderHook(() => useJob('j-1'));
    await waitFor(() => expect(result.current.job?.status).toBe('queued'));
    await waitFor(
      () => expect(result.current.job?.status).toBe('completed'),
      { timeout: 500 },
    );
    expect(result.current.job?.resultRef).toBe('results/abc');
  });
});
