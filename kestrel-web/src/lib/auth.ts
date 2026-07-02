import { apiFetch, setToken, setRefreshToken, clearToken } from "./api";

export interface User {
  id: string;
  email?: string;
  display_name?: string;
  picture_url?: string;
  provider?: string;
  providers?: string[];
  tier?: string;
  is_admin?: boolean;
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  const token = localStorage.getItem("kestrel_token");
  if (!token) return false;

  // Check JWT expiration
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const expiry = payload.exp * 1000;
    if (Date.now() >= expiry) {
      // Token expired — check if refresh token exists
      const refreshToken = localStorage.getItem("kestrel_refresh_token");
      if (!refreshToken) {
        clearToken();
        localStorage.removeItem("kestrel_user");
        return false;
      }
      // Has refresh token — let apiFetch handle the refresh on next call
      return true;
    }
    return true;
  } catch {
    // Malformed token
    clearToken();
    return false;
  }
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("kestrel_user");
  return raw ? JSON.parse(raw) : null;
}

export function storeUser(user: User): void {
  localStorage.setItem("kestrel_user", JSON.stringify(user));
}

export function logout(): void {
  clearToken();
  localStorage.removeItem("kestrel_user");
  window.location.href = "/login";
}

export async function getOAuthUrl(provider: "google" | "line"): Promise<string> {
  const data = await apiFetch<{ authorization_url: string; state: string }>(
    `/auth/oauth/${provider}/authorize`
  );
  // Store state for validation on callback
  sessionStorage.setItem("oauth_state", data.state || "");
  return data.authorization_url;
}

export function handleCallback(token: string, refreshToken?: string, user?: User): void {
  setToken(token);
  if (refreshToken) setRefreshToken(refreshToken);
  if (user) storeUser(user);
  // Sync UI preferences from DB (async, non-blocking)
  syncPreferencesFromDB();
}

async function syncPreferencesFromDB(): Promise<void> {
  try {
    const res = await apiFetch<{ data: { theme: string; language: string; market_preference: string } }>("/user/preferences");
    const prefs = res.data;
    if (prefs.market_preference) {
      localStorage.setItem("kestrel_market_pref", prefs.market_preference);
    }
    if (prefs.language && prefs.language !== "zh-TW") {
      document.cookie = `locale=${prefs.language};path=/;max-age=31536000`;
    }
    // Theme is handled by next-themes via its own cookie — just need to set it
    if (prefs.theme && prefs.theme !== "system") {
      localStorage.setItem("theme", prefs.theme);
    }
  } catch {
    // Non-critical — preferences will use defaults
  }
}
