import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnomaliesPanel } from '../ui/AnomaliesPanel';
import * as api from '../api';

describe('AnomaliesPanel', () => {
  it('loads and renders findings with severity icons', async () => {
    vi.spyOn(api.aiApi, 'anomaly').mockResolvedValue({
      findings: [
        {
          kind: 'missing_values',
          column: 'email',
          severity: 'medium',
          description: '30% null',
        },
        {
          kind: 'outlier',
          column: 'amount',
          severity: 'high',
          description: 'row 42 huge',
        },
      ],
    });
    render(
      <AnomaliesPanel
        ref_="x"
        schema={[]}
        sampleRows={[]}
        summaryStats={{}}
      />,
    );
    fireEvent.click(screen.getByText(/scan for anomalies/i));
    await waitFor(() =>
      expect(screen.getAllByTestId('finding')).toHaveLength(2),
    );
    expect(screen.getByText(/30% null/)).toBeInTheDocument();
    expect(screen.getByText(/row 42 huge/)).toBeInTheDocument();
  });

  it('renders unavailable when capability disabled', async () => {
    vi.spyOn(api.aiApi, 'anomaly').mockRejectedValue(
      new api.AiUnavailableError('AI_CAPABILITY_DISABLED', 'off'),
    );
    render(
      <AnomaliesPanel
        ref_="x"
        schema={[]}
        sampleRows={[]}
        summaryStats={{}}
      />,
    );
    fireEvent.click(screen.getByText(/scan for anomalies/i));
    await waitFor(() =>
      expect(screen.getByTestId('ai-unavailable')).toBeInTheDocument(),
    );
  });
});
