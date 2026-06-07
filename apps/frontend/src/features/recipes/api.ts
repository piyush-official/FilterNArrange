import { authHeaders } from '../../shared/api/client';

export interface Recipe {
  id: string;
  name: string;
  recipe: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface CreateRecipeBody {
  name: string;
  recipe: Record<string, unknown>;
}

const BASE = '/api/v1/recipes';

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    headers: {
      ...(init?.headers as Record<string, string> | undefined),
      ...authHeaders(),
    },
  });
  if (!r.ok) throw new Error(`${init?.method ?? 'GET'} ${path} failed: ${r.status}`);
  return r.status === 204 ? (undefined as unknown as T) : ((await r.json()) as T);
}

export const recipesApi = {
  list: () => jsonFetch<Recipe[]>(BASE),
  get: (id: string) => jsonFetch<Recipe>(`${BASE}/${id}`),
  create: (body: CreateRecipeBody) =>
    jsonFetch<Recipe>(BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  update: (id: string, body: CreateRecipeBody) =>
    jsonFetch<Recipe>(`${BASE}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    jsonFetch<void>(`${BASE}/${id}`, { method: 'DELETE' }),
};
