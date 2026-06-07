import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { UploadService } from '../../../shared/api/generated/services/UploadService';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export interface UploadResult {
  uploadId: string;
  ref: string;
  sizeBytes: number;
}

export async function uploadFile(file: File, token: string): Promise<UploadResult> {
  OpenAPI.TOKEN = token;
  // openapi-typescript-codegen's multipart body uses a FormData under the hood
  const res = await UploadService.upload({ formData: { file } });
  return res as UploadResult;
}

export async function detect(uploadId: string, token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.detect({ requestBody: { uploadId } });
}
