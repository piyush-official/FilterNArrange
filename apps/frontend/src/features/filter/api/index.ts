import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export async function preview(uploadId: string, keep: string[], token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.filterPreview({
    requestBody: { uploadId, filter: { kind: 'column', keep }, sampleSize: 20 },
  });
}
