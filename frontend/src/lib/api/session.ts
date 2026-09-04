/**
 * Canonical AskTrabaajo session.
 *
 * One token pair from POST /api/v1/auth/{register,login,refresh}.
 * Access + refresh live in localStorage under the existing canonical keys
 * so a reload restores the session. Access tokens expire in 15 minutes;
 * POST /auth/refresh rotates the refresh token (replay of a rotated token
 * revokes the whole family — refresh is single-flight for that reason).
 *
 * Do not add a second token scheme. Do not fall back to Supabase/localAuth.
 */
import { API_BASE, RefreshOutcome, createApiClient } from "./client";
import { ApiError, MeResponse, TokenPair } from "./types";

const ACCESS_KEY = "asktrabaajo_at";
const REFRESH_KEY = "asktrabaajo_rt";
const MFA_KEY = "asktrabaajo_mfa_token";
const INTENT_KEY = "asktrabaajo_post_auth_intent";

export type PostAuthIntent = "jobseeker" | "employer";

type SessionListener = () => void;
const listeners = new Set<SessionListener>();

export function subscribeSession(listener: SessionListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function emitSession(): void {
  listeners.forEach((listener) => listener());
}

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getAccessToken(): string | null {
  return storage()?.getItem(ACCESS_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  return storage()?.getItem(REFRESH_KEY) ?? null;
}

export function setSession(pair: {
  access_token: string;
  refresh_token: string;
}): void {
  const store = storage();
  if (!store) return;
  store.setItem(ACCESS_KEY, pair.access_token);
  store.setItem(REFRESH_KEY, pair.refresh_token);
  emitSession();
}

export function clearSession(): void {
  const store = storage();
  if (!store) return;
  store.removeItem(ACCESS_KEY);
  store.removeItem(REFRESH_KEY);
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(MFA_KEY);
  }
  emitSession();
}

export function hasCanonicalSession(): boolean {
  return Boolean(getAccessToken() || getRefreshToken());
}

export function setPostAuthIntent(intent: PostAuthIntent): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(INTENT_KEY, intent);
}

export function takePostAuthIntent(): PostAuthIntent | null {
  if (typeof window === "undefined") return null;
  const value = window.sessionStorage.getItem(INTENT_KEY);
  window.sessionStorage.removeItem(INTENT_KEY);
  if (value === "employer" || value === "jobseeker") return value;
  return null;
}

/** Authed API client — the single controlled data-access boundary. */
export const api = createApiClient(() => getAccessToken());

async function rotateRefreshToken(): Promise<RefreshOutcome> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return "invalid";

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
      credentials: "include",
    });
  } catch {
    return "network";
  }

  const text = await response.text();
  let payload: TokenPair | { error?: { message?: string } } | null = null;
  if (text) {
    try {
      payload = JSON.parse(text) as TokenPair;
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    clearSession();
    return "invalid";
  }
  const pair = payload as TokenPair;
  if (!pair?.access_token || !pair?.refresh_token) {
    clearSession();
    return "invalid";
  }
  setSession(pair);
  return "rotated";
}

api.setRefreshHandler(rotateRefreshToken);
api.setOnUnauthorized(() => {
  clearSession();
});

export async function refreshSession(): Promise<RefreshOutcome> {
  return rotateRefreshToken();
}

export async function fetchMe(): Promise<MeResponse | null> {
  if (!hasCanonicalSession()) return null;
  try {
    return await api.get<MeResponse>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export interface LoginOutcome {
  ok: boolean;
  mfaRequired?: boolean;
  message?: string;
}

export async function login(email: string, password: string): Promise<LoginOutcome> {
  const result = await api.post<{
    mfa_required: boolean;
    mfa_token?: string | null;
    access_token?: string | null;
    refresh_token?: string | null;
  }>("/auth/login", { email, password });
  if (result.mfa_required) {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(MFA_KEY, result.mfa_token ?? "");
    }
    return { ok: false, mfaRequired: true };
  }
  if (result.access_token && result.refresh_token) {
    setSession({
      access_token: result.access_token,
      refresh_token: result.refresh_token,
    });
    return { ok: true };
  }
  return { ok: false, message: "Unexpected login response." };
}

export async function registerAccount(
  email: string,
  password: string,
  fullName: string
): Promise<LoginOutcome> {
  const pair = await api.post<TokenPair>("/auth/register", {
    email,
    password,
    full_name: fullName,
  });
  setSession(pair);
  return { ok: true };
}

export async function completeMfa(code: string): Promise<LoginOutcome> {
  const mfaToken =
    typeof window !== "undefined" ? window.sessionStorage.getItem(MFA_KEY) ?? "" : "";
  const pair = await api.post<TokenPair>("/auth/mfa/verify", {
    mfa_token: mfaToken,
    code,
  });
  setSession(pair);
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(MFA_KEY);
  }
  return { ok: true };
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    } catch {
      // local cleanup regardless
    }
  }
  clearSession();
}
