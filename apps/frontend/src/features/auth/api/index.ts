import { AuthService } from '../../../shared/api/generated/services/AuthService';
import { configureApi } from '../../../shared/api/client';

export interface AuthSession {
  token: string;
  user: { id: string; email: string; displayName?: string | null };
}

export async function signup(email: string, password: string, displayName?: string): Promise<AuthSession> {
  configureApi(null);
  const res = await AuthService.signup({ requestBody: { email, password, displayName } });
  return res as AuthSession;
}

export async function login(email: string, password: string): Promise<AuthSession> {
  configureApi(null);
  const res = await AuthService.login({ requestBody: { email, password } });
  return res as AuthSession;
}

export async function me(token: string) {
  configureApi(token);
  return AuthService.me();
}
