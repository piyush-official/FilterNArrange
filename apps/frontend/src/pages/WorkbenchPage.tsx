import { useState } from 'react';
import { Dropzone, DetectionPanel, useUpload } from '../features/upload';
import { ColumnPicker, PreviewTable, useFilter } from '../features/filter';
import { FormatChooser, DownloadButton, useDownload } from '../features/download';
import { useAuth } from '../features/auth';

export function WorkbenchPage() {
  const { user, logout } = useAuth();
  const up = useUpload();
  const columnNames = up.schema.map(c => c.name);
  const flt = useFilter(up.uploadId, columnNames);
  const dl = useDownload();
  const [fmt, setFmt] = useState<'csv' | 'json'>('csv');

  return (
    <main>
      <header>
        <h1>FilterNArrange</h1>
        <div>{user?.email} <button onClick={logout}>Log out</button></div>
      </header>
      <Dropzone onSelect={up.select} />
      {up.busy && <p>Working…</p>}
      {up.error && <p role="alert">{up.error}</p>}
      {up.format && (
        <DetectionPanel format={up.format} confidence={up.confidence!} schema={up.schema} />
      )}
      {columnNames.length > 0 && (
        <>
          <ColumnPicker columns={columnNames} selected={flt.selected} onChange={flt.setSelected} />
          <PreviewTable columns={flt.selected} rows={flt.rows} />
          <FormatChooser value={fmt} onChange={setFmt} />
          <DownloadButton busy={dl.busy}
            disabled={!up.uploadId || flt.selected.length === 0}
            onClick={() => up.uploadId && dl.run(up.uploadId, flt.selected, fmt)} />
          {dl.error && <p role="alert">{dl.error}</p>}
        </>
      )}
    </main>
  );
}
