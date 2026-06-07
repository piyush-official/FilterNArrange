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
    // Delay the WS push so the REST seed (microtask) lands first and the
    // hook walks status: undefined → queued → completed.
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
      80,
    );
    return () => {};
  },
}));

describe('useJob', () => {
  it('absorbs a WS completion envelope into the job state', async () => {
    const { result } = renderHook(() => useJob('j-1'));
    await waitFor(
      () => expect(result.current.job?.status).toBe('completed'),
      { timeout: 1000 },
    );
    expect(result.current.job?.resultRef).toBe('results/abc');
    expect(result.current.progress).toBe(100);
  });
});
