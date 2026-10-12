import type {
  AuthResponse,
  FieldDetail,
  ForgotPasswordResponse,
  MessageResponse,
  User,
} from "./types";

/**
 * Where the API lives. Same origin by default ("/api": Docker + nginx, or the Vite dev proxy).
 * On Vercel the API is on another host, so VITE_API_URL is set at build time, for example
 * https://codescope-api.onrender.com  (the "/api" part is added for you if you forget it).
 */
export function resolveApiBase(raw: string | undefined): string {
  let base = (raw ?? "").trim().replace(/\/+$/, "");
  if (!base) return "/api";
  if (/^https?:\/\//i.test(base) && !/\/api$/i.test(base)) base += "/api";
  return base;
}

const BASE = resolveApiBase(import.meta.env.VITE_API_URL);
const REFRESH_KEY = "codescope.refresh_token";

let accessToken: string | null = null;
let onAuthFailure: (() => void) | null = null;

export function setAuthFailureHandler(fn: (() => void) | null) {
  onAuthFailure = fn;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: FieldDetail[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------- tokens
export const authStorage = {
  hasRefreshToken: () => !!localStorage.getItem(REFRESH_KEY),
  save(resp: AuthResponse) {
    accessToken = resp.access_token;
    localStorage.setItem(REFRESH_KEY, resp.refresh_token);
  },
  clear() {
    accessToken = null;
    localStorage.removeItem(REFRESH_KEY);
  },
  refreshToken: () => localStorage.getItem(REFRESH_KEY),
};

// ------------------------------------------------------------- plumbing
async function rawFetch(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Cannot reach the CodeScope server. If it was idle it may be waking up, so wait a minute and try again.",
    );
  }
}

async function parseBody(res: Response): Promise<unknown> {
  if (res.status === 204) return null;
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function toError(res: Response, body: unknown): ApiError {
  const e = (body as { error?: { code?: string; message?: string; details?: FieldDetail[] } })?.error;
  return new ApiError(
    res.status,
    e?.code ?? "http_error",
    e?.message ?? `Request failed (${res.status}).`,
    e?.details ?? [],
  );
}

// ------------------------------------------------------- token refresh
let refreshing: Promise<AuthResponse | null> | null = null;

/** All callers share one in-flight refresh (the refresh token is single-use). */
export function refreshSession(): Promise<AuthResponse | null> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

async function doRefresh(): Promise<AuthResponse | null> {
  const token = authStorage.refreshToken();
  if (!token) return null;
  try {
    const res = await rawFetch("/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token }),
    });
    if (!res.ok) {
      // Only a definite rejection ends the session; a 5xx should not log the user out.
      if (res.status === 401) authStorage.clear();
      return null;
    }
    const data = (await res.json()) as AuthResponse;
    authStorage.save(data);
    return data;
  } catch {
    return null; // network error: keep the token and let the user retry
  }
}

// -------------------------------------------------------------- request
interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

export async function request<T>(
  path: string,
  { method = "GET", body, auth = true }: RequestOptions = {},
): Promise<T> {
  const send = () => {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
    return rawFetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  };

  let res = await send();

  if (res.status === 401 && auth) {
    const session = await refreshSession();
    if (session) {
      res = await send();
    } else {
      accessToken = null;
      if (!authStorage.hasRefreshToken()) onAuthFailure?.();
    }
  }

  const data = await parseBody(res);
  if (!res.ok) throw toError(res, data);
  return data as T;
}

// ------------------------------------------------------------ auth calls
export const authApi = {
  async register(name: string, email: string, password: string) {
    const resp = await request<AuthResponse>("/auth/register", {
      method: "POST",
      body: { name, email, password },
      auth: false,
    });
    authStorage.save(resp);
    return resp.user;
  },

  async login(email: string, password: string) {
    const resp = await request<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    authStorage.save(resp);
    return resp.user;
  },

  async logout() {
    const refresh_token = authStorage.refreshToken();
    authStorage.clear();
    if (refresh_token) {
      try {
        await request<null>("/auth/logout", { method: "POST", body: { refresh_token }, auth: false });
      } catch {
        /* the local session is already gone; the server token will simply expire */
      }
    }
  },

  me: () => request<User>("/auth/me"),

  forgotPassword: (email: string) =>
    request<ForgotPasswordResponse>("/auth/forgot-password", {
      method: "POST",
      body: { email },
      auth: false,
    }),

  resetPassword: (token: string, new_password: string) =>
    request<MessageResponse>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password },
      auth: false,
    }),
};
