import { FormEvent, useState } from 'react';

interface Props {
  onSubmit: (creds: { email: string; password: string }) => Promise<void>;
}

export function LoginForm({ onSubmit }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    setBusy(true); setError(null);
    try { await onSubmit({ email, password }); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" value={email}
             onChange={e => setEmail(e.target.value)} required />
      <label htmlFor="password">Password</label>
      <input id="password" type="password" value={password}
             onChange={e => setPassword(e.target.value)} required minLength={8} />
      <button type="submit" disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</button>
      {error && <div role="alert">{error}</div>}
    </form>
  );
}
