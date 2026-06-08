import * as React from 'react';
import {
  listAdminFormatRequests,
  transitionFormatRequest,
  type AdminFormatRequest,
  type FormatRequestStatus,
} from './api';

const NEXT_STATUSES: FormatRequestStatus[] = [
  'triaged',
  'in-progress',
  'shipped',
  'rejected',
];

/**
 * Plan F §T35 — admin-only triage page. The route is gated server-side
 * (SecurityConfig restricts /api/v1/admin/** to ROLE_ADMIN).
 */
export function AdminFormatRequestsPage() {
  const [rows, setRows] = React.useState<AdminFormatRequest[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    try {
      setRows(await listAdminFormatRequests());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const handleTransition = async (
    id: string,
    next: FormatRequestStatus,
  ) => {
    try {
      await transitionFormatRequest(id, next);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  if (error) return <div role="alert">{error}</div>;
  if (rows === null) return <div>Loading…</div>;

  return (
    <section data-testid="admin-format-requests">
      <h2>Format requests (open)</h2>
      {rows.length === 0 ? (
        <p>No open format requests.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Created</th>
              <th>Label</th>
              <th>Sample ref</th>
              <th>Status</th>
              <th>Transition</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-testid="admin-fr-row">
                <td>{r.created_at}</td>
                <td>{r.user_label ?? '—'}</td>
                <td>
                  <code>{r.sample_ref}</code>
                </td>
                <td>{r.status}</td>
                <td>
                  {NEXT_STATUSES.filter((s) => s !== r.status).map((s) => (
                    <button
                      key={s}
                      onClick={() => handleTransition(r.id, s)}
                    >
                      → {s}
                    </button>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
