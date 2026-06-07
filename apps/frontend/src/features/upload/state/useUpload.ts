import { useState } from 'react';
import { useAuth } from '../../auth';
import * as uploadApi from '../api';

export interface DetectedSchemaColumn { name: string; type: string; nullable: boolean }

export function useUpload() {
  const { token } = useAuth();
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [format, setFormat] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [schema, setSchema] = useState<DetectedSchemaColumn[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function select(file: File) {
    if (!token) { setError('You must be logged in'); return; }
    setBusy(true); setError(null);
    try {
      const up = await uploadApi.uploadFile(file, token);
      setUploadId(up.uploadId);
      const det = await uploadApi.detect(up.uploadId, token);
      setFormat(det.format); setConfidence(det.confidence);
      setSchema(det.schema as DetectedSchemaColumn[]);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return { uploadId, format, confidence, schema, error, busy, select };
}
