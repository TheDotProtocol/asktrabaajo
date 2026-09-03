/**
 * AskTrabaajo canonical API client — the future single data-access boundary.
 *
 * Phase 3 scope: this module only establishes the boundary (types + auth'd
 * fetch + error envelope). Pages are NOT migrated yet — each route group
 * switches to this client in later phases, per the approved architecture.
 *
 * Base URL: NEXT_PUBLIC_API_URL (defaults to the same origin's /api).
 * Every future endpoint lives under {base}/api/v1.
 */
import { ApiError, ApiEnvelope } from "./types";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "") + "/api/v1";

export class ApiClient {
  constructor(
    private readonly baseUrl: string = API_BASE,
    private readonly getAccessToken: () => string | null = () => null
  ) {}

  /** Refresh token hook — wired when the auth flow migrates (Phase 5+). */
  private onUnauthorized: () => void = () => {};

  setOnUnauthorized(handler: () => void): void {
    this.onUnauthorized = handler;
  }

  async request<T>(
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    path: string,
    body?: unknown
  ): Promise<T> {
    const token = this.getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "include",
    });

    if (response.status === 401) {
      this.onUnauthorized();
    }

    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;

    if (!response.ok) {
      throw new ApiError(
        (payload as ApiEnvelope | null)?.error?.code ?? "http_error",
        (payload as ApiEnvelope | null)?.error?.message ??
          `Request failed (${response.status})`,
        response.status
      );
    }
    return payload as T;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }
  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }
  put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PUT", path, body);
  }
  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PATCH", path, body);
  }
  delete<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }
}

/** Default client instance. */
export const api = new ApiClient();
