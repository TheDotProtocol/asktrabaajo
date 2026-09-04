'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  completeMfa,
  fetchMe,
  hasCanonicalSession,
  login as sessionLogin,
  logout as sessionLogout,
  registerAccount,
  setPostAuthIntent,
  subscribeSession,
  takePostAuthIntent,
  type LoginOutcome,
  type PostAuthIntent,
} from '@/lib/api/session';
import { ApiError, MeResponse } from '@/lib/api/types';

interface AuthContextValue {
  me: MeResponse | null;
  loading: boolean;
  error: string;
  login: (email: string, password: string) => Promise<LoginOutcome & { me: MeResponse | null }>;
  register: (
    email: string,
    password: string,
    fullName: string,
    intent?: PostAuthIntent
  ) => Promise<LoginOutcome & { me: MeResponse | null }>;
  verifyMfa: (code: string) => Promise<LoginOutcome & { me: MeResponse | null }>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
  consumeIntent: () => PostAuthIntent | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const hydrate = useCallback(async () => {
    if (!hasCanonicalSession()) {
      setMe(null);
      setError('');
      setLoading(false);
      return;
    }
    try {
      const profile = await fetchMe();
      setMe(profile);
      setError('');
    } catch (err) {
      if (err instanceof ApiError && err.code === 'network_error') {
        setError(err.message);
      } else {
        setMe(null);
        setError(err instanceof Error ? err.message : 'Unable to restore session.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void hydrate();
    return subscribeSession(() => {
      void hydrate();
    });
  }, [hydrate]);

  const afterAuth = useCallback(async (outcome: LoginOutcome) => {
    if (!outcome.ok) return { ...outcome, me: null };
    const profile = await fetchMe();
    setMe(profile);
    return { ...outcome, me: profile };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setError('');
      try {
        const outcome = await sessionLogin(email, password);
        return afterAuth(outcome);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : 'Unable to sign in. Please try again.';
        setError(message);
        return { ok: false, message, me: null };
      }
    },
    [afterAuth]
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      fullName: string,
      intent?: PostAuthIntent
    ) => {
      setError('');
      if (intent) setPostAuthIntent(intent);
      try {
        const outcome = await registerAccount(email, password, fullName);
        return afterAuth(outcome);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : 'Unable to create the account.';
        setError(message);
        return { ok: false, message, me: null };
      }
    },
    [afterAuth]
  );

  const verifyMfa = useCallback(
    async (code: string) => {
      setError('');
      try {
        const outcome = await completeMfa(code);
        return afterAuth(outcome);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : 'Unable to verify the authentication code.';
        setError(message);
        return { ok: false, message, me: null };
      }
    },
    [afterAuth]
  );

  const logout = useCallback(async () => {
    await sessionLogout();
    setMe(null);
    setError('');
  }, []);

  const consumeIntent = useCallback(() => takePostAuthIntent(), []);

  const value = useMemo(
    () => ({
      me,
      loading,
      error,
      login,
      register,
      verifyMfa,
      logout,
      reload: hydrate,
      consumeIntent,
    }),
    [me, loading, error, login, register, verifyMfa, logout, hydrate, consumeIntent]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useCanonicalAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useCanonicalAuth must be used within AuthProvider');
  }
  return ctx;
}
