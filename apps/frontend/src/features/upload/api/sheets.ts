import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';

export interface SheetsResponse {
  sheets: string[];
}

/**
 * GET /api/v1/uploads/{id}/sheets. fetch-based; the OpenAPI codegen client
 * hasn't been regenerated against the 1.1 spec yet.
 */
export async function listSheets(uploadId: string, token: string): Promise<string[]> {
  const base = (OpenAPI.BASE as string) ?? '/api/v1';
  const res = await fetch(`${base}/uploads/${uploadId}/sheets`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`listSheets failed: ${res.status} ${body}`);
  }
  const json = (await res.json()) as SheetsResponse;
  return json.sheets ?? [];
}
