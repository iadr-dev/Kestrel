"use client";

import { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import { createPortal } from "react-dom";

type ToastKind = "error" | "success" | "info";
interface Toast { id: number; message: string; kind: ToastKind }

interface ToastApi {
  show: (message: string, kind?: ToastKind) => void;
  error: (message: string) => void;
  success: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

/** Toast feedback — replaces native alert(). Auto-dismisses; stacks bottom-center. */
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}

const KIND_STYLES: Record<ToastKind, string> = {
  error: "bg-down/15 border-down/40 text-foreground",
  success: "bg-up/15 border-up/40 text-foreground",
  info: "bg-signal/15 border-signal/30 text-foreground",
};
const KIND_ICON: Record<ToastKind, string> = { error: "⚠️", success: "✓", info: "ℹ️" };

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  // Portal target (document.body) only exists on the client. Gating on a
  // post-mount flag — rather than `typeof document` — keeps the server and the
  // first client render identical, avoiding a hydration mismatch.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((message: string, kind: ToastKind = "info") => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { id, message, kind }]);
    setTimeout(() => dismiss(id), 4000);
  }, [dismiss]);

  const api: ToastApi = {
    show,
    error: useCallback((m: string) => show(m, "error"), [show]),
    success: useCallback((m: string) => show(m, "success"), [show]),
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      {mounted && createPortal(
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[2000] flex flex-col items-center gap-2 pointer-events-none">
          {toasts.map((t) => (
            <div
              key={t.id}
              onClick={() => dismiss(t.id)}
              className={`pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-2xl border shadow-lg backdrop-blur-sm text-sm font-medium cursor-pointer animate-in slide-in-from-bottom ${KIND_STYLES[t.kind]}`}
            >
              <span>{KIND_ICON[t.kind]}</span>
              <span>{t.message}</span>
            </div>
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}
