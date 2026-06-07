/// <reference types="vite/client" />
import { OpenAPI } from './generated/core/OpenAPI';

const SESSION_STORAGE_KEY = 'fna.session';

export function configureApi(token: string | null) {
  OpenAPI.BASE = (import.meta.env.VITE_API_BASE as string) ?? '/api/v1';
  OpenAPI.TOKEN = token ?? undefined;
}

function readToken(): string | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as { token?: string };
    return s.token ?? null;
  } catch {
    return null;
  }
}

export function authHeaders(): Record<string, string> {
  const t = readToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
