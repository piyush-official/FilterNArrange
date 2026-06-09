import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export interface PreviewSchemaColumn {
  name: string;
  type: string;
  nullable: boolean;
}

export interface PreviewResponse {
  schema: PreviewSchemaColumn[];
  rows: Array<Record<string, unknown>>;
}

export async function preview(uploadId: string, keep: string[], token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.filterPreview({
    requestBody: { uploadId, filter: { kind: 'column', keep }, sampleSize: 20 },
  });
}

/**
 * Generic preview that accepts any filter kind (column / row / expression /
 * regex). Plan C T16 widened the gateway contract; openapi-typescript-codegen
 * hasn't been regenerated against the new oneOf shape yet, so we hit the
 * route with fetch() directly. Same wire shape, just an untyped filter slot.
 */
export async function previewAny(
  uploadId: string,
  filter: Record<string, unknown>,
  token: string,
  sampleSize: number = 20,
): Promise<PreviewResponse> {
  const base = (OpenAPI.BASE as string) ?? '/api/v1';
  const res = await fetch(`${base}/filter/preview`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ uploadId, filter, sampleSize }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`preview failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<PreviewResponse>;
}
