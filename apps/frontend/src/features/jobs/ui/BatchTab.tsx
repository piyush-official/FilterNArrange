import * as React from 'react';
import { submitJob } from '../api/jobsClient';
import { JobProgressCard } from './JobProgressCard';

export function BatchTab() {
  const [running, setRunning] = React.useState<string[]>([]);

  async function submit() {
    const j = await submitJob({
      kind: 'batch-filter',
      params: {},
    });
    setRunning((prev) => [j.jobId, ...prev]);
  }

  return (
    <section className="batch-tab">
      <h2>Batch (paid)</h2>
      <p>Submit large filter / convert / analyze jobs that run in the background.</p>
      <button onClick={submit}>Submit batch job</button>
      <div className="batch-tab__running">
        {running.map((id) => (
          <JobProgressCard key={id} jobId={id} />
        ))}
      </div>
    </section>
  );
}
