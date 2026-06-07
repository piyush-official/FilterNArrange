import { useEffect, useState } from 'react';
import { useAuth } from '../../auth';
import { listSheets } from '../api/sheets';

interface Props {
  uploadId: string;
  picked: string | null;
  onPick: (sheet: string) => void;
}

export function SheetPicker({ uploadId, picked, onPick }: Props) {
  const { token } = useAuth();
  const [sheets, setSheets] = useState<string[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setSheets(null); setErr(null);
    listSheets(uploadId, token)
      .then(s => { if (!cancelled) setSheets(s); })
      .catch(e => { if (!cancelled) setErr((e as Error).message); });
    return () => { cancelled = true; };
  }, [uploadId, token]);

  if (err) return <div role="alert">{err}</div>;
  if (!sheets) return <div>Loading sheets…</div>;
  if (sheets.length === 0) return <div>No sheets found.</div>;
  return (
    <section className="sheet-picker" aria-label="Pick a sheet">
      <h3>Pick a sheet</h3>
      <ul>
        {sheets.map(s => (
          <li key={s}>
            <button
              type="button"
              aria-pressed={picked === s}
              className={picked === s ? 'sheet sheet-active' : 'sheet'}
              onClick={() => onPick(s)}
            >
              {s}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
