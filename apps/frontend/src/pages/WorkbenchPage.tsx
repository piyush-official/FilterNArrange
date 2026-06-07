import { useEffect, useMemo, useState } from 'react';
import { Dropzone, DetectionPanel, useUpload } from '../features/upload';
import {
  ColumnPicker, PreviewTable, useFilter,
  FilterModePicker, type FilterMode,
  RowFilterForm, type RowPredicate,
  RegexFilterForm, type RegexFilterSpec,
} from '../features/filter';
import { FormatChooser, DownloadButton, useDownload } from '../features/download';
import { useAuth } from '../features/auth';

export function WorkbenchPage() {
  const { user, logout } = useAuth();
  const up = useUpload();
  const columnNames = up.schema.map(c => c.name);

  const [mode, setMode] = useState<FilterMode>('column');
  const [keep, setKeep] = useState<string[]>([]);
  const [rowSpec, setRowSpec] = useState<RowPredicate>({ col: '', op: 'eq', value: '' });
  const [exprSpec, setExprSpec] = useState<{ expr: string }>({ expr: '' });
  const [regexSpec, setRegexSpec] = useState<RegexFilterSpec>({ pattern: '', flags: [] });

  useEffect(() => {
    setKeep(columnNames);
    const first = columnNames[0];
    if (first && !rowSpec.col) {
      setRowSpec(p => ({ ...p, col: first }));
    }
  }, [columnNames.join('|')]);

  const filterSpec = useMemo<Record<string, unknown> | null>(() => {
    switch (mode) {
      case 'column':
        return keep.length > 0 ? { kind: 'column', keep } : null;
      case 'row':
        return rowSpec.col ? { kind: 'row', predicate: rowSpec } : null;
      case 'expression':
        return exprSpec.expr ? { kind: 'expression', expr: exprSpec.expr } : null;
      case 'regex':
        return regexSpec.pattern
          ? { kind: 'regex', pattern: regexSpec.pattern, flags: regexSpec.flags }
          : null;
    }
  }, [mode, keep, rowSpec, exprSpec, regexSpec]);

  const flt = useFilter(up.uploadId, filterSpec);
  const dl = useDownload();
  const [fmt, setFmt] = useState<'csv' | 'json'>('csv');

  const previewColumns = flt.schema.length ? flt.schema.map(c => c.name) : columnNames;

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
          <FilterModePicker mode={mode} onChange={setMode} />
          {mode === 'column' && (
            <ColumnPicker columns={columnNames} selected={keep} onChange={setKeep} />
          )}
          {mode === 'row' && (
            <RowFilterForm schema={up.schema} value={rowSpec} onChange={setRowSpec} />
          )}
          {mode === 'expression' && (
            <label>
              Expression:
              <textarea
                aria-label="expression-input"
                rows={3}
                style={{ width: '100%' }}
                value={exprSpec.expr}
                onChange={e => setExprSpec({ expr: e.target.value })}
                placeholder="age > 18 AND country = 'IN'"
              />
            </label>
          )}
          {mode === 'regex' && (
            <RegexFilterForm value={regexSpec} onChange={setRegexSpec} />
          )}
          {flt.busy && <p>Filtering…</p>}
          {flt.error && <p role="alert">{flt.error}</p>}
          <PreviewTable columns={previewColumns} rows={flt.rows} />
          <FormatChooser value={fmt} onChange={setFmt} />
          <DownloadButton
            busy={dl.busy}
            disabled={!up.uploadId || keep.length === 0}
            onClick={() => up.uploadId && dl.run(up.uploadId, keep, fmt)}
          />
          {dl.error && <p role="alert">{dl.error}</p>}
        </>
      )}
    </main>
  );
}
