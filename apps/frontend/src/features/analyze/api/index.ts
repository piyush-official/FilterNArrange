import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';

export interface AnalyzeResponse {
  kind: string;
  payload: Record<string, unknown>;
  warnings: string[];
}

/**
 * POST /api/v1/analyze. Plan C T16 added the endpoint; openapi-typescript-codegen
 * hasn't been regenerated against the new spec yet, so we use fetch() directly
 * (same pattern as filter/api previewAny). The wire shape matches the
 * gateway's AnalyzeRequest record: camelCase `uploadId`, optional `filter`.
 */
export async function analyze(
  uploadId: string,
  kind: string,
  options: Record<string, unknown>,
  token: string,
  filter?: Record<string, unknown>,
): Promise<AnalyzeResponse> {
  const base = (OpenAPI.BASE as string) ?? '/api/v1';
  const res = await fetch(`${base}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      uploadId,
      analysis: { kind, options },
      filter,
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`analyze failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<AnalyzeResponse>;
}
