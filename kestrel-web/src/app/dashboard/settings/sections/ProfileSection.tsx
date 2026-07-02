"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";

function ConnectedAccount({
  name,
  connected,
  icon,
  color,
  provider,
}: {
  name: string;
  connected: boolean;
  icon: React.ReactNode;
  color: string;
  provider: string;
}) {
  const t = useTranslations("settings.notifications");

  const handleConnect = async () => {
    try {
      // Pass link_user param so backend knows to link to existing account
      const res = await apiFetch<{ authorization_url: string }>(`/auth/oauth/${provider}/authorize?link=true`);
      if (res.authorization_url) {
        // Store that we're linking (not fresh login)
        sessionStorage.setItem("oauth_link_mode", "true");
        window.location.href = res.authorization_url;
      }
    } catch { /* silent */ }
  };

  return (
    <div className="flex items-center justify-between p-3 border border-border/40 rounded-2xl">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: `${color}15` }}>
          {icon}
        </div>
        <div>
          <span className="text-sm font-medium">{name}</span>
          {connected && (
            <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-up/10 text-up font-medium">{t("connected")}</span>
          )}
        </div>
      </div>
      {!connected && (
        <button onClick={handleConnect} className="px-3 py-1.5 text-xs border border-border/40 rounded-2xl hover:bg-raised transition-colors text-muted">
          {t("connect")}
        </button>
      )}
    </div>
  );
}

export function ProfileSection() {
  const t = useTranslations("settings.profile");
  const [user, setUser] = useState<{
    display_name?: string;
    picture_url?: string;
    provider?: string;
    providers?: string[];
  } | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem("kestrel_user");
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });

  useEffect(() => {
    apiFetch<{ id: string; display_name: string; picture_url: string | null; tier: string }>("/user/profile")
      .then((res) => setUser((prev) => ({ ...prev, display_name: res.display_name, picture_url: res.picture_url || undefined })))
      .catch((err) => logError("ProfileSection.load", err));
  }, []);

  const providers = user?.providers || (user?.provider ? [user.provider] : []);

  return (
    <div>
      <h2 className="text-lg font-bold mb-6">{t("title")}</h2>
      <div className="max-w-md space-y-6">
        {/* Avatar + name */}
        <div className="flex items-center gap-4">
          {user?.picture_url ? (
            // Plain <img>: avatar comes from arbitrary OAuth CDNs (Google/LINE);
            // next/image would require whitelisting every provider host in
            // next.config remotePatterns. referrerPolicy avoids leaking the page URL.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={user.picture_url} referrerPolicy="no-referrer"
              alt={user.display_name || ""}
              className="w-14 h-14 rounded-full border border-border object-cover"
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-signal/20 flex items-center justify-center">
              <span className="text-lg font-bold text-signal">
                {(user?.display_name || "U")[0]}
              </span>
            </div>
          )}
          <div>
            <div className="text-base font-semibold">{user?.display_name || "User"}</div>
            <div className="text-xs text-muted mt-0.5">
              {providers.includes("line") && providers.includes("google")
                ? `${t("via_google")} + ${t("via_line")}`
                : providers.includes("line") ? t("via_line")
                : providers.includes("google") ? t("via_google")
                : t("not_logged_in")}
            </div>
          </div>
        </div>

        {/* Connected accounts */}
        <div className="pt-4 border-t border-border">
          <p className="text-xs font-medium text-muted mb-3">{t("connected")}</p>
          <div className="space-y-2">
            <ConnectedAccount
              name="LINE"
              connected={providers.includes("line")}
              provider="line"
              icon={
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="#06C755">
                  <path d="M24 10.304c0-5.369-5.383-9.738-12-9.738-6.616 0-12 4.369-12 9.738 0 4.814 4.269 8.846 10.036 9.608.391.084.922.258 1.057.592.121.303.079.778.039 1.085l-.171 1.027c-.053.303-.242 1.186 1.039.647 1.281-.54 6.911-4.069 9.428-6.967C23.101 14.479 24 12.515 24 10.304zM8.497 12.934a.29.29 0 01-.29.29H5.572a.29.29 0 01-.29-.29V8.801a.29.29 0 01.29-.29h.29a.29.29 0 01.29.29v3.553h1.645a.29.29 0 01.29.29v.29zm1.93 0a.29.29 0 01-.29.29h-.29a.29.29 0 01-.29-.29V8.801a.29.29 0 01.29-.29h.29a.29.29 0 01.29.29v4.133zm5.088 0a.29.29 0 01-.29.29h-.29a.29.29 0 01-.253-.148l-1.858-2.511v2.369a.29.29 0 01-.29.29h-.29a.29.29 0 01-.29-.29V8.801a.29.29 0 01.29-.29h.29a.29.29 0 01.253.148l1.858 2.511V8.801a.29.29 0 01.29-.29h.29a.29.29 0 01.29.29v4.133zm3.078-3.553a.29.29 0 01-.29.29h-1.645v.871h1.645a.29.29 0 01.29.29v.29a.29.29 0 01-.29.29h-1.645v.871h1.645a.29.29 0 01.29.29v.29a.29.29 0 01-.29.29h-2.225a.29.29 0 01-.29-.29V8.801a.29.29 0 01.29-.29h2.225a.29.29 0 01.29.29v.29a.29.29 0 01-.29.29h-1.645z"/>
                </svg>
              }
              color="#06C755"
            />
            <ConnectedAccount
              name="Google"
              connected={providers.includes("google")}
              provider="google"
              icon={
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              }
              color="#4285F4"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
