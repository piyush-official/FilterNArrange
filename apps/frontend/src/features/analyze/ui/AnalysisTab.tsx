import { useState } from 'react';
import { ChartsPanel } from './ChartsPanel';
import { GroupByPanel } from './GroupByPanel';
import { SchemaPanel } from './SchemaPanel';
import { SummaryPanel } from './SummaryPanel';

type SubTab = 'summary' | 'group_by' | 'charts' | 'schema';

interface Props {
  uploadId: string;
  shape: 'tabular' | 'tree';
  filter?: Record<string, unknown>;
}

export function AnalysisTab({ uploadId, shape, filter }: Props) {
  const [sub, setSub] = useState<SubTab>('summary');
  const tabularOnly = shape === 'tabular';
  const treeOnly = shape === 'tree';
  return (
    <div className="analysis-tab">
      <div role="tablist" aria-label="Analysis">
        <button role="tab" aria-selected={sub === 'summary'}  onClick={() => setSub('summary')}>Summary</button>
        <button role="tab" aria-selected={sub === 'group_by'} onClick={() => setSub('group_by')} disabled={!tabularOnly}>Group-by</button>
        <button role="tab" aria-selected={sub === 'charts'}   onClick={() => setSub('charts')}   disabled={!tabularOnly}>Charts</button>
        <button role="tab" aria-selected={sub === 'schema'}   onClick={() => setSub('schema')}   disabled={!treeOnly}>Schema</button>
      </div>
      <div className="panel">
        {sub === 'summary'  && <SummaryPanel  uploadId={uploadId} filter={filter} />}
        {sub === 'group_by' && <GroupByPanel  uploadId={uploadId} filter={filter} />}
        {sub === 'charts'   && <ChartsPanel   uploadId={uploadId} filter={filter} />}
        {sub === 'schema'   && <SchemaPanel   uploadId={uploadId} filter={filter} />}
      </div>
    </div>
  );
}
