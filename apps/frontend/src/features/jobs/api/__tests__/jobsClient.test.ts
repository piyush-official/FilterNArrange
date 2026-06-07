import { describe, expect, it, vi, beforeEach } from 'vitest';
import { submitJob, getJob } from '../jobsClient';

describe('jobsClient', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('POST /api/v1/jobs includes Idempotency-Key header', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ jobId: 'j-1', status: 'queued' }), {
        status: 202,
      }),
    );
    await submitJob({ kind: 'batch-filter', params: {} });
    const init = fetchSpy.mock.calls[0]![1] as RequestInit;
    const headers = new Headers(init.headers as HeadersInit);
    expect(headers.get('Idempotency-Key')).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    );
  });

  it('GET /api/v1/jobs/:id maps response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ jobId: 'j-1', status: 'running' })),
    );
    const r = await getJob('j-1');
    expect(r.status).toBe('running');
  });

  it('attaches Authorization header when a session token is stored', async () => {
    localStorage.setItem(
      'fna.session',
      JSON.stringify({ token: 'tok-xyz', user: { id: 'u1' } }),
    );
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ jobId: 'j-1', status: 'running' })),
    );
    await getJob('j-1');
    const init = fetchSpy.mock.calls[0]![1] as RequestInit;
    const headers = new Headers(init.headers as HeadersInit);
    expect(headers.get('Authorization')).toBe('Bearer tok-xyz');
  });
});
