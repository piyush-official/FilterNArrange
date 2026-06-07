import { OpenAPI } from './generated/core/OpenAPI';

export function configureApi(token: string | null) {
  OpenAPI.BASE = (import.meta.env.VITE_API_BASE as string) ?? '/api/v1';
  OpenAPI.TOKEN = token ?? undefined;
}
