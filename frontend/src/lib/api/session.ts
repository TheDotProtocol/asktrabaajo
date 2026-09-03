/**
 * Client-side auth session for the canonical identity flows (Phase 4 proof).
 *
 * Tokens live in localStorage for the functional proof pages. Production UI
 * (Phase 7+) will move access tokens to memory with refresh-token handling —
 * the API boundary stays identical.
 */
import { createApiClient } from "./client";
import { MeResponse, TokenPair } from "./types";

const ACCESS_KEY = "asktrabaajo_at";
const REFRESH_KEY = "asktrabaajo_rt";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setSession(pair: {
  access_token: string;
  refresh_token: string;
}): void {
  window.localStorage.setItem(ACCESS_KEY, pair.access_token);
  window.localStorage.setItem(REFRESH_KEY, pair.refresh_token);
}

export function clearSession(): void {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

/** Authed API client — the single controlled data-access boundary. */
export const api = createApiClient(() => getAccessToken());
api.setOnUnauthorized(() => clearSession());

export async function fetchMe(): Promise<MeResponse | null> {
  if (!getAccessToken()) return null;
  try {
    return await api.get<MeResponse>("/auth/me");
  } catch {
    clearSession();
    return null;
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
    sessionStorage.setItem("asktrabaajo_mfa_token", result.mfa_token ?? "");
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

export async function completeMfa(code: string): Promise<LoginOutcome> {
  const mfaToken = sessionStorage.getItem("asktrabaajo_mfa_token") ?? "";
  const pair = await api.post<TokenPair>("/auth/mfa/verify", {
    mfa_token: mfaToken,
    code,
  });
  setSession(pair);
  sessionStorage.removeItem("asktrabaajo_mfa_token");
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
