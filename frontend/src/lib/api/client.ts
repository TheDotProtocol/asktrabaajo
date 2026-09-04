/**
 * Canonical AskTrabaajo API client — the single data-access boundary.
 *
 * Base URL: NEXT_PUBLIC_API_URL (defaults to http://localhost:8000).
 * Every canonical endpoint lives under {base}/api/v1.
 *
 * 401 handling: rotate the refresh token once (single-flight), retry the
 * original request, then surface unauthorized. Auth endpoints never retry.
 */
import { ApiError, ApiEnvelope } from "./types";

export const API_ORIGIN = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export const API_BASE = `${API_ORIGIN}/api/v1`;

const NO_REFRESH_RETRY = new Set([
  "/auth/login",
  "/auth/register",
  "/auth/refresh",
  "/auth/logout",
  "/auth/mfa/verify",
  "/auth/forgot-password",
  "/auth/reset-password",
]);

export type RefreshOutcome = "rotated" | "invalid" | "network";

export class ApiClient {
  private onUnauthorized: () => void = () => {};
  private refreshAccessToken: (() => Promise<RefreshOutcome>) | null = null;
  private refreshInFlight: Promise<RefreshOutcome> | null = null;

  constructor(
    private readonly baseUrl: string = API_BASE,
    private readonly getAccessToken: () => string | null = () => null
  ) {}

  setOnUnauthorized(handler: () => void): void {
    this.onUnauthorized = handler;
  }

  setRefreshHandler(handler: () => Promise<RefreshOutcome>): void {
    this.refreshAccessToken = handler;
  }

  private async rotate(): Promise<RefreshOutcome> {
    if (!this.refreshAccessToken) return "invalid";
    if (!this.refreshInFlight) {
      this.refreshInFlight = this.refreshAccessToken().finally(() => {
        this.refreshInFlight = null;
      });
    }
    return this.refreshInFlight;
  }

  async request<T>(
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    path: string,
    body?: unknown,
    extraHeaders?: Record<string, string>,
    isRetry = false
  ): Promise<T> {
    const token = this.getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(extraHeaders ?? {}),
    };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: "include",
      });
    } catch {
      throw new ApiError(
        "network_error",
        "Unable to reach AskTrabaajo. Check your connection and try again.",
        0
      );
    }

    if (
      response.status === 401 &&
      !isRetry &&
      !NO_REFRESH_RETRY.has(path) &&
      this.refreshAccessToken
    ) {
      const outcome = await this.rotate();
      if (outcome === "rotated") {
        return this.request<T>(method, path, body, extraHeaders, true);
      }
      if (outcome === "invalid") {
        this.onUnauthorized();
      }
      // network: keep existing tokens; caller sees a 401/network error
    } else if (response.status === 401 && NO_REFRESH_RETRY.has(path) === false) {
      this.onUnauthorized();
    }

    const text = await response.text();
    let payload: unknown = null;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      const envelope = payload as ApiEnvelope | null;
      throw new ApiError(
        envelope?.error?.code ?? "http_error",
        envelope?.error?.message ?? `Request failed (${response.status})`,
        response.status
      );
    }
    return payload as T;
  }

  get<T>(path: string, extraHeaders?: Record<string, string>): Promise<T> {
    return this.request<T>("GET", path, undefined, extraHeaders);
  }
  post<T>(path: string, body?: unknown, extraHeaders?: Record<string, string>): Promise<T> {
    return this.request<T>("POST", path, body, extraHeaders);
  }
  put<T>(path: string, body?: unknown, extraHeaders?: Record<string, string>): Promise<T> {
    return this.request<T>("PUT", path, body, extraHeaders);
  }
  patch<T>(path: string, body?: unknown, extraHeaders?: Record<string, string>): Promise<T> {
    return this.request<T>("PATCH", path, body, extraHeaders);
  }
  delete<T>(path: string, extraHeaders?: Record<string, string>): Promise<T> {
    return this.request<T>("DELETE", path, undefined, extraHeaders);
  }
}

/** Create a client whose auth token is read live from a provider. */
export function createApiClient(
  getAccessToken: () => string | null
): ApiClient {
  return new ApiClient(API_BASE, getAccessToken);
}

/** Default client instance (no token provider — use lib/api/session for UI). */
export const api = new ApiClient();
