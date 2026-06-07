import { authHeaders } from '../../shared/api/client';

export type FormatRequestStatus =
  | 'open'
  | 'triaged'
  | 'in-progress'
  | 'shipped'
  | 'rejected';

export interface FormatRequest {
  id: string;
  sampleRef: string;
  userLabel: string | null;
  status: FormatRequestStatus;
  priority: number;
  githubIssue: number | null;
  createdAt: string;
}

export async function submitFormatRequest(
  sampleRef: string, userLabel: string | null,
): Promise<FormatRequest> {
  const r = await fetch('/api/v1/format-requests', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ sampleRef, userLabel }),
  });
  if (!r.ok) throw new Error(`format-request submit failed: ${r.status}`);
  return r.json();
}

export interface AdminFormatRequest {
  id: string;
  user_id: string;
  sample_ref: string;
  user_label: string | null;
  status: FormatRequestStatus;
  priority: number;
  github_issue: number | null;
  created_at: string;
  resolved_at: string | null;
}

export async function listAdminFormatRequests(): Promise<AdminFormatRequest[]> {
  const r = await fetch('/api/v1/admin/format-requests', { headers: authHeaders() });
  if (!r.ok) throw new Error(`admin list failed: ${r.status}`);
  return r.json();
}

export async function transitionFormatRequest(
  id: string,
  status: FormatRequestStatus,
  githubIssue?: number,
): Promise<AdminFormatRequest> {
  const r = await fetch(`/api/v1/admin/format-requests/${id}/transition`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ status, githubIssue: githubIssue ?? null }),
  });
  if (!r.ok) throw new Error(`transition failed: ${r.status}`);
  return r.json();
}
