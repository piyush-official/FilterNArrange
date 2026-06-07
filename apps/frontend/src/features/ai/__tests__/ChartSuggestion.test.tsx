import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ChartSuggestion } from '../ui/ChartSuggestion';
import * as api from '../api';

describe('ChartSuggestion', () => {
  it('renders the suggested chart info', async () => {
    vi.spyOn(api.aiApi, 'chartSuggest').mockResolvedValue({
      recommended_chart: {
        kind: 'bar',
        x: 'country',
        y: 'count',
        justification: 'Categorical x with numeric y.',
      },
    });
    render(
      <ChartSuggestion ref_="x" schema={[]} cardinality={{}} skip={false} />,
    );
    await waitFor(() => expect(screen.getByText(/bar/i)).toBeInTheDocument());
    expect(
      screen.getByText(/Categorical x with numeric y\./),
    ).toBeInTheDocument();
  });
});
