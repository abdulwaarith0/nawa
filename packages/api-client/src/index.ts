// Transport-agnostic typed client over the {code,message,data} envelope.
// Runs in the browser, in Node SSR, and in tests with an injected fetchImpl.
// No framework imports.

import type { Envelope } from "@nawa/contracts";

export class ApiError extends Error {
  status: number;
  code: number;
  constructor(status: number, code: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface ApiClientConfig {
  baseUrl: string;
  getAccessToken?: () => string | null | undefined;
  getRefreshToken?: () => string | null | undefined;
  onTokens?: (tokens: Tokens) => void;
  onAuthError?: () => void;
  headers?: Record<string, string>;
  credentials?: RequestCredentials;
  fetchImpl?: typeof fetch;
}

export interface ApiClient {
  get<T = unknown>(path: string): Promise<T>;
  post<T = unknown>(path: string, body?: unknown): Promise<T>;
  patch<T = unknown>(path: string, body?: unknown): Promise<T>;
  put<T = unknown>(path: string, body?: unknown): Promise<T>;
  delete<T = unknown>(path: string): Promise<T>;
  refreshSession(): Promise<boolean>;
  auth: {
    login(identifier: string, password: string): Promise<unknown>;
    signup(input: unknown): Promise<unknown>;
    me(): Promise<unknown>;
    logout(): Promise<unknown>;
  };
}

async function parseEnvelope(res: Response): Promise<Envelope> {
  const text = await res.text();
  try {
    return JSON.parse(text) as Envelope;
  } catch {
    // Synthesize an envelope for non-JSON bodies.
    return { code: res.status, message: text || res.statusText, data: null };
  }
}

export function createApiClient(config: ApiClientConfig): ApiClient {
  const doFetch = config.fetchImpl ?? fetch;
  // One shared in-flight refresh promise — the refresh token is single-use, so
  // two concurrent 401s must not both spend it.
  let inflightRefresh: Promise<boolean> | null = null;

  async function refreshSession(): Promise<boolean> {
    if (inflightRefresh) return inflightRefresh;
    const run = async (): Promise<boolean> => {
      try {
        const refreshToken = config.getRefreshToken?.();
        const res = await doFetch(`${config.baseUrl}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: config.credentials,
          body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
        });
        if (!res.ok) return false;
        const env = await parseEnvelope(res);
        const data = env.data as Tokens | null;
        if (data?.access_token) {
          config.onTokens?.(data);
          return true;
        }
        return false;
      } catch {
        return false;
      }
    };
    inflightRefresh = run();
    try {
      return await inflightRefresh;
    } finally {
      inflightRefresh = null;
    }
  }

  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
    retried = false,
  ): Promise<T> {
    // FormData bodies (multipart uploads) must NOT be JSON-stringified, and
    // must NOT get an explicit Content-Type — fetch sets the multipart
    // boundary itself only when it constructs that header.
    const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...config.headers,
    };
    const token = config.getAccessToken?.();
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await doFetch(`${config.baseUrl}${path}`, {
      method,
      headers,
      credentials: config.credentials,
      body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
    });

    if (res.status === 401) {
      if (!retried) {
        const refreshed = await refreshSession();
        if (refreshed) {
          return request<T>(method, path, body, true);
        }
      }
      // Either the refresh failed, or the replayed request still 401'd —
      // the session is unusable.
      config.onAuthError?.();
    }

    const env = await parseEnvelope(res);
    if (res.ok) {
      return env.data as T;
    }
    throw new ApiError(res.status, env.code ?? res.status, env.message ?? res.statusText);
  }

  return {
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body),
    patch: (path, body) => request("PATCH", path, body),
    put: (path, body) => request("PUT", path, body),
    delete: (path) => request("DELETE", path),
    refreshSession,
    auth: {
      login: (identifier, password) => request("POST", "/auth/login", { identifier, password }),
      signup: (input) => request("POST", "/auth/signup", input),
      me: () => request("GET", "/auth/me"),
      logout: () => request("POST", "/auth/logout"),
    },
  };
}
