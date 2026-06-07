import * as React from 'react';

export function AiUnavailable({ message }: { message?: string }) {
  return (
    <div role="status" aria-live="polite" data-testid="ai-unavailable">
      AI feature unavailable.
      {message ? <div className="ai-unavailable__detail">{message}</div> : null}
    </div>
  );
}
