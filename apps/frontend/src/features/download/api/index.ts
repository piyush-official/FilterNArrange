import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export async function convert(uploadId: string, keep: string[],
                              outputFormat: 'csv' | 'json', token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.convert({
    requestBody: { uploadId, filter: { kind: 'column', keep }, outputFormat },
  });
}

export function downloadUrl(resultId: string): string {
  const base = (OpenAPI.BASE as string) ?? '/api/v1';
  return `${base}/download/${resultId}`;
}
