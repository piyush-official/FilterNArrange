import { FormEvent, useState } from 'react';

interface Props {
  onSubmit: (data: { email: string; password: string; displayName?: string }) => Promise<void>;
}

export function SignupForm({ onSubmit }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!email || password.length < 8) return;
    setBusy(true); setError(null);
    try { await onSubmit({ email, password, displayName: displayName || undefined }); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
      <label htmlFor="password">Password</label>
      <input id="password" type="password" value={password}
             onChange={e => setPassword(e.target.value)} required minLength={8} />
      <label htmlFor="displayName">Display name</label>
      <input id="displayName" value={displayName} onChange={e => setDisplayName(e.target.value)} />
      <button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Sign up'}</button>
      {error && <div role="alert">{error}</div>}
    </form>
  );
}
