import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LoginForm, useAuth } from '../features/auth';
import {
  type AuthConfig,
  buildKeycloakLoginUrl,
  fetchAuthConfig,
  randomCodeVerifier,
  sha256Base64Url,
} from '../features/auth/authConfig';

const PKCE_STATE_KEY = 'fna.oidc.state';
const PKCE_VERIFIER_KEY = 'fna.oidc.verifier';

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [cfg, setCfg] = useState<AuthConfig | null>(null);

  useEffect(() => {
    fetchAuthConfig()
      .then(setCfg)
      .catch(() => setCfg({ provider: 'spring-jwt' }));
  }, []);

  if (cfg === null) return <main>Loading…</main>;

  if (cfg.provider === 'keycloak') {
    const startOidc = async () => {
      const verifier = randomCodeVerifier();
      const challenge = await sha256Base64Url(verifier);
      const state = randomCodeVerifier();
      sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
      sessionStorage.setItem(PKCE_STATE_KEY, state);
      const url = buildKeycloakLoginUrl(
        cfg,
        `${location.origin}/auth/callback`,
        challenge,
        state,
      );
      location.assign(url);
    };
    return (
      <main>
        <h1>Log in</h1>
        <p>This deployment uses OIDC. Sign in via your identity provider.</p>
        <button onClick={startOidc}>Continue to single sign-on</button>
      </main>
    );
  }

  return (
    <main>
      <h1>Log in</h1>
      <LoginForm
        onSubmit={async ({ email, password }) => {
          await login(email, password);
          nav('/');
        }}
      />
    </main>
  );
}
