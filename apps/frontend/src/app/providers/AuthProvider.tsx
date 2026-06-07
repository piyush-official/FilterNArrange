import { createContext, ReactNode, useEffect, useState, useCallback } from 'react';
import * as authApi from '../../features/auth/api';
import { configureApi } from '../../shared/api/client';

interface AuthState {
  token: string | null;
  user: authApi.AuthSession['user'] | null;
  signup: (e: string, p: string, dn?: string) => Promise<void>;
  login: (e: string, p: string) => Promise<void>;
  logout: () => void;
}

const STORAGE_KEY = 'fna.session';

export const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<authApi.AuthSession['user'] | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const s = JSON.parse(raw) as authApi.AuthSession;
        setToken(s.token); setUser(s.user); configureApi(s.token);
      } catch { /* corrupt — clear */ localStorage.removeItem(STORAGE_KEY); }
    }
  }, []);

  const persist = useCallback((s: authApi.AuthSession) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    setToken(s.token); setUser(s.user); configureApi(s.token);
  }, []);

  const signup = useCallback(async (email: string, password: string, displayName?: string) => {
    persist(await authApi.signup(email, password, displayName));
  }, [persist]);

  const login = useCallback(async (email: string, password: string) => {
    persist(await authApi.login(email, password));
  }, [persist]);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null); setUser(null); configureApi(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, signup, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
