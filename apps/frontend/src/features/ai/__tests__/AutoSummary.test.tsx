import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AutoSummary } from '../ui/AutoSummary';
import * as api from '../api';

describe('AutoSummary', () => {
  it('auto-fetches and renders the summary', async () => {
    vi.spyOn(api.aiApi, 'summary').mockResolvedValue({
      summary: 'Sales by region',
      key_observations: ['IN is largest'],
    });
    render(
      <AutoSummary
        ref_="x"
        schema={[]}
        sampleRows={[]}
        totalRows={10}
        totalSizeBytes={100}
        skip={false}
      />,
    );
    await waitFor(() =>
      expect(screen.getByText(/Sales by region/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/IN is largest/)).toBeInTheDocument();
  });

  it('does not call API when skip=true', async () => {
    const spy = vi.spyOn(api.aiApi, 'summary').mockResolvedValue({
      summary: 'x',
      key_observations: [],
    });
    render(
      <AutoSummary
        ref_="x"
        schema={[]}
        sampleRows={[]}
        totalRows={0}
        totalSizeBytes={0}
        skip={true}
      />,
    );
    await new Promise((r) => setTimeout(r, 10));
    expect(spy).not.toHaveBeenCalled();
  });

  it('renders AI unavailable on capability disabled', async () => {
    vi.spyOn(api.aiApi, 'summary').mockRejectedValue(
      new api.AiUnavailableError('AI_CAPABILITY_DISABLED', 'off'),
    );
    render(
      <AutoSummary
        ref_="x"
        schema={[]}
        sampleRows={[]}
        totalRows={0}
        totalSizeBytes={0}
        skip={false}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId('ai-unavailable')).toBeInTheDocument(),
    );
  });
});
