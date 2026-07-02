"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/components/ui/Toast";
import { useServerEvents } from "@/hooks/useServerEvents";
import { useState } from "react";
import type React from "react";

/** Mounts the single app-wide SSE push subscription (must be inside the
 *  QueryClientProvider so it can invalidate caches on server events). */
function ServerEvents() {
  useServerEvents();
  return null;
}

// Suppress React 19 false-positive warning about next-themes script injection
if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  const originalError = console.error;
  console.error = (...args: unknown[]) => {
    if (
      typeof args[0] === "string" &&
      args[0].includes("Encountered a script tag")
    ) {
      return;
    }
    originalError.apply(console, args);
  };
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        gcTime: 30 * 60 * 1000,
        // Refetch a query when the user returns to the tab — but only if it's
        // already stale (past its staleTime). This lets backend cache busts
        // (e.g. after a cron ingest) surface without a manual refresh, while
        // staying cheap: focusing the tab won't refetch fresh data.
        refetchOnWindowFocus: true,
        refetchOnMount: false,
        retry: 1,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <ServerEvents />
      <NextThemesProvider
        attribute="class"
        defaultTheme="dark"
        enableSystem
        disableTransitionOnChange
      >
        <ToastProvider>{children}</ToastProvider>
      </NextThemesProvider>
    </QueryClientProvider>
  );
}
