import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { useAuth } from '../../auth';
import { analyze } from '../api';

interface VLEncoding {
  field: string;
  type: string;
}

type SeriesDatum = Array<string | number>;

interface ChartSpec {
  mark: 'point' | 'bar' | 'line';
  score: number;
  rationale: string;
  spec: { encoding: { x: VLEncoding; y: VLEncoding } };
  data?: SeriesDatum[];
}

interface Props {
  uploadId: string;
  filter?: Record<string, unknown>;
}

function vlToECharts(c: ChartSpec) {
  const { x, y } = c.spec.encoding;
  return {
    title: { text: `${c.mark}: ${x.field} × ${y.field}` },
    tooltip: {},
    xAxis: {
      name: x.field,
      type: x.type === 'temporal' ? 'time'
          : x.type === 'quantitative' ? 'value'
          : 'category',
    },
    yAxis: {
      name: y.field,
      type: y.type === 'quantitative' ? 'value' : 'category',
    },
    series: [{
      type: c.mark === 'point' ? 'scatter'
          : c.mark === 'line' ? 'line'
          : 'bar',
      data: c.data ?? [],
    }],
  };
}

export function ChartsPanel({ uploadId, filter }: Props) {
  const { token } = useAuth();
  const [charts, setCharts] = useState<ChartSpec[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setCharts(null); setErr(null);
    analyze(uploadId, 'chart_suggest', {}, token, filter)
      .then(r => {
        if (!cancelled) setCharts((r.payload.charts ?? []) as ChartSpec[]);
      })
      .catch(e => { if (!cancelled) setErr((e as Error).message); });
    return () => { cancelled = true; };
  }, [uploadId, token, JSON.stringify(filter)]);

  if (err) return <div role="alert">{err}</div>;
  if (!charts) return <div>Loading chart suggestions…</div>;
  if (charts.length === 0) return <div>No chart suggestions for this schema.</div>;
  return (
    <div>
      {charts.map((c, i) => (
        <div key={i} className="chart-card">
          <h4>{c.rationale} <small>(score {c.score})</small></h4>
          <ReactECharts option={vlToECharts(c)} style={{ height: 280 }} />
        </div>
      ))}
    </div>
  );
}
