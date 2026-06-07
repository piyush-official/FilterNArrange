import * as React from 'react';
import { submitFormatRequest } from './api';
import { useBilling } from '../billing';

/**
 * Plan F §T34 — banner shown when detect fails to identify a format.
 * Paid users can submit a request directly; free users see an upgrade CTA.
 */
export function FormatRequestBanner({
  sampleRef,
}: {
  sampleRef: string;
}) {
  const { data: billing } = useBilling();
  const [label, setLabel] = React.useState('');
  const [status, setStatus] = React.useState<'idle' | 'submitting' | 'sent' | 'error'>(
    'idle',
  );
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  const submit = async () => {
    setStatus('submitting');
    setErrorMsg(null);
    try {
      await submitFormatRequest(sampleRef, label.trim() || null);
      setStatus('sent');
    } catch (e: unknown) {
      setStatus('error');
      setErrorMsg(e instanceof Error ? e.message : String(e));
    }
  };

  if (billing?.tier !== 'paid') {
    return (
      <aside data-testid="format-request-banner" className="format-request-banner">
        <p>
          We couldn't auto-detect this format. <strong>Paid users</strong> can
          request support — <a href="/account/billing">upgrade to request</a>.
        </p>
      </aside>
    );
  }

  if (status === 'sent') {
    return (
      <aside data-testid="format-request-banner" data-status="sent">
        Format request submitted. We'll mirror it to GitHub for tracking.
      </aside>
    );
  }

  return (
    <aside data-testid="format-request-banner" className="format-request-banner">
      <p>Request support for this format.</p>
      <input
        placeholder="Optional: name (e.g. 'fixed-width payroll')"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
      />
      <button onClick={submit} disabled={status === 'submitting'}>
        {status === 'submitting' ? 'Submitting…' : 'Request this format'}
      </button>
      {errorMsg && <div role="alert">{errorMsg}</div>}
    </aside>
  );
}
