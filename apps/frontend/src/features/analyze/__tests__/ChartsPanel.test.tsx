import { describe, it, expect, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { ChartsPanel } from '../ui/ChartsPanel';
import * as analyzeApi from '../api';

// Capture the option ReactECharts is called with so we can inspect the
// series.data without rendering an actual canvas (which jsdom can't draw).
const echartsOption = vi.hoisted(() => ({ current: null as unknown }));
vi.mock('echarts-for-react', () => ({
  default: (props: { option: unknown }) => {
    echartsOption.current = props.option;
    return null;
  },
}));

vi.mock('../../auth', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

describe('ChartsPanel', () => {
  it('renders ECharts series with the data the plugin emits', async () => {
    vi.spyOn(analyzeApi, 'analyze').mockResolvedValue({
      kind: 'chart_suggest',
      payload: {
        charts: [
          {
            mark: 'bar',
            score: 0.85,
            rationale: 'categorical × numeric → bar',
            spec: {
              encoding: {
                x: { field: 'country', type: 'nominal' },
                y: { field: 'count', type: 'quantitative' },
              },
            },
            data: [['US', 42], ['UK', 17]],
          },
        ],
      },
      warnings: [],
    });

    render(<ChartsPanel uploadId="u1" />);

    await waitFor(() => expect(echartsOption.current).not.toBeNull());
    const opt = echartsOption.current as { series: [{ data: unknown }] };
    expect(opt.series[0].data).toEqual([['US', 42], ['UK', 17]]);
  });
});
