import { describe, it, expect, vi, beforeEach } from 'vitest';
import { aiApi, AiError, AiUnavailableError } from '../api';

describe('aiApi', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(),
    );
  });

  it('nlToFilter posts the right body', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        filter_spec: { kind: 'row' },
        confidence: 0.9,
      }),
    });
    const out = await aiApi.nlToFilter({ ref: 'x', query: 'q', schema: [] });
    expect(out.filter_spec.kind).toBe('row');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/ai/nl-to-filter',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('maps AI_CAPABILITY_DISABLED to AiUnavailableError', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ code: 'AI_CAPABILITY_DISABLED', message: 'off' }),
    });
    await expect(
      aiApi.anomaly({ ref: 'x' }),
    ).rejects.toBeInstanceOf(AiUnavailableError);
  });

  it('maps other errors to AiError with code + status', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => ({ code: 'AI_LLM_ERROR', message: 'ouch' }),
    });
    await expect(
      aiApi.summary({
        ref: 'x',
        schema: [],
        sample_rows: [],
        total_rows: 0,
        total_size_bytes: 0,
      }),
    ).rejects.toMatchObject({ name: 'AiError', code: 'AI_LLM_ERROR', status: 502 });
  });
});
