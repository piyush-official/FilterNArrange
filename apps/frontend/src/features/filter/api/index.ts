import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { ColumnFilterSpec } from '../../../shared/api/generated/models/ColumnFilterSpec';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export async function preview(uploadId: string, keep: string[], token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.filterPreview({
    requestBody: { uploadId, filter: { kind: ColumnFilterSpec.kind.COLUMN, keep }, sampleSize: 20 },
  });
}
