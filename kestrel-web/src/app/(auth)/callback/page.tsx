"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { handleCallback } from "@/lib/auth";

function CallbackHandler() {
  const t = useTranslations("auth");
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    const refreshToken = searchParams.get("refresh_token");
    const userJson = searchParams.get("user");

    if (token) {
      const user = userJson ? JSON.parse(decodeURIComponent(userJson)) : undefined;
      handleCallback(token, refreshToken || undefined, user);

      // Clean the URL (remove tokens from browser history)
      window.history.replaceState({}, "", "/callback");

      // If linking account from settings, go back to settings
      const isLinking = sessionStorage.getItem("oauth_link_mode");
      if (isLinking) {
        sessionStorage.removeItem("oauth_link_mode");
        router.replace("/dashboard/settings");
      } else {
        router.replace("/dashboard");
      }
    } else {
      const error = searchParams.get("error");
      router.replace(`/login${error ? `?error=${error}` : ""}`);
    }
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-signal border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-muted">{t("logging_in")}</p>
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <CallbackHandler />
    </Suspense>
  );
}
