const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export class ApiError extends Error {
  public kind: "client" | "server" | "network";
  constructor(public status: number, public data: Record<string, unknown>) {
    const err = data?.error as Record<string, unknown> | undefined;
    super((err?.message as string) || `API Error ${status}`);
    this.kind = status >= 500 ? "server" : status >= 400 ? "client" : "network";
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kestrel_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kestrel_refresh_token");
}

export function setToken(token: string): void {
  localStorage.setItem("kestrel_token", token);
}

export function setRefreshToken(token: string): void {
  localStorage.setItem("kestrel_refresh_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("kestrel_token");
  localStorage.removeItem("kestrel_refresh_token");
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  if (isRefreshing && refreshPromise) return refreshPromise;

  isRefreshing = true;
  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return false;

      const data = await res.json();
      if (data.access_token) {
        setToken(data.access_token);
        if (data.refresh_token) setRefreshToken(data.refresh_token);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function apiFetch<T = unknown>(
  path: string,
  opts?: RequestInit
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(opts?.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers, signal: opts?.signal || AbortSignal.timeout(30000) });

  if (res.status === 401) {
    // Try refresh token
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // Retry with new token
      const newToken = getToken();
      const retryHeaders: HeadersInit = {
        "Content-Type": "application/json",
        ...(opts?.headers || {}),
        ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
      };
      const retryRes = await fetch(`${API_BASE}${path}`, { ...opts, headers: retryHeaders });
      if (!retryRes.ok) {
        const data = await retryRes.json().catch(() => ({}));
        throw new ApiError(retryRes.status, data);
      }
      return retryRes.json();
    }

    // Refresh failed — session expired, redirect to login
    clearToken();
    localStorage.removeItem("kestrel_user");
    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      window.location.href = "/login?session_expired=true";
    }
    throw new ApiError(401, { error: { message: "Session expired" } });
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, data);
  }

  return res.json();
}

export function apiStreamUrl(path: string): string {
  return `${API_BASE}${path}`;
}

