/**
 * Plan G §T5 — discovery client for the gateway's /api/v1/auth/config
 * endpoint. The result is cached in localStorage so the login UI doesn't
 * blank-flash on every visit.
 */
export type AuthProvider = 'spring-jwt' | 'keycloak';

export interface AuthConfig {
  provider: AuthProvider;
  issuer?: string;
  client_id?: string;
}

const CACHE_KEY = 'fna.auth-config';

export async function fetchAuthConfig(): Promise<AuthConfig> {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      return JSON.parse(cached) as AuthConfig;
    }
  } catch {
    // localStorage may be disabled — fall through to network fetch.
  }
  const r = await fetch('/api/v1/auth/config');
  if (!r.ok) throw new Error(`auth/config failed: ${r.status}`);
  const cfg = (await r.json()) as AuthConfig;
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(cfg));
  } catch {
    // best-effort cache
  }
  return cfg;
}

/**
 * Build the Keycloak authorization-code URL with PKCE. Caller stores the
 * verifier in sessionStorage keyed on the returned state.
 */
export function buildKeycloakLoginUrl(
  cfg: AuthConfig,
  redirectUri: string,
  codeChallenge: string,
  state: string,
): string {
  if (!cfg.issuer || !cfg.client_id) {
    throw new Error('keycloak config missing issuer / client_id');
  }
  const url = new URL(`${cfg.issuer}/protocol/openid-connect/auth`);
  url.searchParams.set('client_id', cfg.client_id);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('scope', 'openid profile email');
  url.searchParams.set('code_challenge', codeChallenge);
  url.searchParams.set('code_challenge_method', 'S256');
  url.searchParams.set('state', state);
  return url.toString();
}

/** Generate a PKCE code_verifier (43-128 chars from the unreserved set). */
export function randomCodeVerifier(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

export async function sha256Base64Url(input: string): Promise<string> {
  const buf = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest('SHA-256', buf);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}
