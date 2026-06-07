import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

// Stub useAuth so panels' useEffect can read a token.
vi.mock('../../src/features/auth', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

// Stub the analyze API so no network is needed.
vi.mock('../../src/features/analyze/api', () => ({
  analyze: vi.fn().mockResolvedValue({
    kind: 'summary_stats',
    payload: { columns: [] },
    warnings: [],
  }),
}));

// Stub echarts-for-react so we don't have to bundle ECharts in this test.
vi.mock('echarts-for-react', () => ({
  __esModule: true,
  default: () => <div data-testid="echarts" />,
}));

import { AnalysisTab } from '../../src/features/analyze/ui/AnalysisTab';


describe('AnalysisTab', () => {
  it('renders summary tab selected by default', () => {
    render(<AnalysisTab uploadId="u1" shape="tabular" />);
    expect(screen.getByRole('tab', { name: /^summary$/i })).toHaveAttribute('aria-selected', 'true');
  });

  it('disables Schema for tabular shape', () => {
    render(<AnalysisTab uploadId="u1" shape="tabular" />);
    expect(screen.getByRole('tab', { name: /^schema$/i })).toBeDisabled();
    expect(screen.getByRole('tab', { name: /^group-by$/i })).not.toBeDisabled();
  });

  it('disables Group-by + Charts for tree shape', () => {
    render(<AnalysisTab uploadId="u1" shape="tree" />);
    expect(screen.getByRole('tab', { name: /^group-by$/i })).toBeDisabled();
    expect(screen.getByRole('tab', { name: /^charts$/i })).toBeDisabled();
    expect(screen.getByRole('tab', { name: /^schema$/i })).not.toBeDisabled();
  });

  it('switches sub-tab on click', () => {
    render(<AnalysisTab uploadId="u1" shape="tabular" />);
    fireEvent.click(screen.getByRole('tab', { name: /^charts$/i }));
    expect(screen.getByRole('tab', { name: /^charts$/i })).toHaveAttribute('aria-selected', 'true');
  });
});
