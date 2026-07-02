"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { useTranslations } from "next-intl";
import type { PetPullResult } from "@/types";

type Phase = "idle" | "shaking" | "bursting" | "revealed" | "no_pulls";

const RARITY_RING: Record<string, string> = {
  legendary: "border-legendary/60 shadow-[0_0_40px_rgba(255,95,74,0.4)]",
  rare: "border-signal/50 shadow-[0_0_32px_rgba(201,162,0,0.35)]",
  uncommon: "border-up/40 shadow-[0_0_24px_rgba(34,197,94,0.3)]",
  common: "border-border/50",
};

const RARITY_TEXT: Record<string, string> = {
  legendary: "text-legendary",
  rare: "text-signal",
  uncommon: "text-up",
  common: "text-muted",
};

const CONFETTI_COLORS = ["#C9A200", "#FF5F4A", "#22C55E", "#3B82F6", "#A855F7", "#FFD700"];

/** Full-screen gacha modal: an animated gift box that bursts open to reveal the
 *  pulled pet. Mirrors the market StockSearch command-palette modal (portal +
 *  blurred backdrop + Escape-to-close). The parent performs the actual pull and
 *  drives `phase`/`result`; this component owns the presentation + animation. */
export function PetGachaModal({
  open,
  phase,
  result,
  petIcon,
  onClose,
  onPull,
  availablePulls,
}: {
  open: boolean;
  phase: Phase;
  result: PetPullResult | null;
  petIcon: (petId: string, rarity: string) => React.ReactNode;
  onClose: () => void;
  onPull: () => void;
  availablePulls: number;
}) {
  const t = useTranslations("pet");

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      // Don't let Escape close mid-burst — let the reveal land.
      if (e.key === "Escape" && (phase === "idle" || phase === "revealed" || phase === "no_pulls")) {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, phase, onClose]);

  // Portal target only exists in the browser; skip during SSR.
  if (!open || typeof document === "undefined") return null;

  const rarity = result?.pet?.rarity || "common";
  const busy = phase === "shaking" || phase === "bursting";

  return createPortal(
    <div
      className="fixed inset-0 z-[1500] flex items-center justify-center px-4 bg-black/60 backdrop-blur-md animate-in fade-in duration-200"
      onClick={() => { if (!busy) onClose(); }}
    >
      <div
        className="relative w-full max-w-sm rounded-3xl border border-border/40 bg-surface p-8 shadow-2xl animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        {!busy && (
          <button
            onClick={onClose}
            aria-label="Close"
            className="absolute top-3 right-3 p-1.5 text-muted hover:text-foreground hover:bg-raised rounded-lg transition-colors"
          >
            ✕
          </button>
        )}

        <h3 className="text-center text-sm font-bold text-foreground mb-1">{t("title")}</h3>
        <p className="text-center text-[11px] text-muted mb-6">
          {t("available", { count: availablePulls })}
        </p>

        {/* Stage */}
        <div className="relative h-48 flex items-center justify-center mb-6 select-none">
          {/* Radial rays during the burst */}
          {phase === "bursting" && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div
                className="w-40 h-40 rounded-full animate-ray-burst"
                style={{
                  background:
                    "radial-gradient(circle, rgba(255,215,0,0.55) 0%, rgba(255,215,0,0.15) 40%, transparent 70%)",
                }}
              />
            </div>
          )}

          {/* Confetti during burst/reveal */}
          {(phase === "bursting" || phase === "revealed") && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              {Array.from({ length: 14 }).map((_, i) => {
                const angle = (i / 14) * Math.PI * 2;
                const dist = 70 + (i % 3) * 22;
                return (
                  <span
                    key={i}
                    className="absolute w-2 h-2 rounded-sm animate-confetti-fly"
                    style={{
                      backgroundColor: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
                      ["--tx" as string]: `${Math.cos(angle) * dist}px`,
                      ["--ty" as string]: `${Math.sin(angle) * dist}px`,
                      ["--rot" as string]: `${(i % 2 ? 1 : -1) * 360}deg`,
                      animationDelay: `${(i % 5) * 30}ms`,
                    }}
                  />
                );
              })}
            </div>
          )}

          {/* Closed / shaking / bursting gift box */}
          {(phase === "idle" || phase === "shaking" || phase === "bursting") && (
            <span
              className={`text-7xl drop-shadow-[0_0_16px_rgba(201,162,0,0.55)] ${
                phase === "shaking"
                  ? "animate-gacha-shake"
                  : phase === "bursting"
                  ? "animate-gift-burst"
                  : "animate-gift-idle"
              }`}
            >
              🎁
            </span>
          )}

          {/* Revealed pet — ALWAYS shows the actual pet pulled, for both a brand
              new pet and a duplicate. A duplicate adds the XP / level-up line
              beneath the pet (previously the duplicate branch skipped the pet
              entirely and only showed a generic ✦ + XP, so the pulled pet never
              appeared). */}
          {phase === "revealed" && (result?.status === "new" || result?.status === "duplicate") && result.pet && (
            <div className={`flex flex-col items-center gap-2 rounded-2xl border-2 px-6 py-4 bg-raised/30 animate-gacha-pop ${RARITY_RING[rarity]}`}>
              <span className="flex items-center justify-center">{petIcon(result.pet.id, rarity)}</span>
              <div className="text-center">
                <div className="text-base font-bold text-foreground">{result.pet.name_zh}</div>
                <div className={`text-[11px] font-bold uppercase tracking-wide ${RARITY_TEXT[rarity]}`}>
                  {rarity}
                </div>
                {result.status === "new" ? (
                  <div className="text-[11px] font-bold text-up mt-1">{t("pull_result_new")}</div>
                ) : (
                  <div className="text-[11px] font-medium text-signal mt-1">
                    {t("pull_result_dup_xp", { xp: result.xp_gained ?? 0 })}
                    {result.leveled_up && (
                      <span className="ml-1.5 text-legendary font-bold">↑ {t("pull_result_leveled", { level: result.new_level ?? 0 })}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* No pulls */}
          {phase === "no_pulls" && (
            <div className="flex flex-col items-center gap-2">
              <span className="text-5xl opacity-50">🎁</span>
              <div className="text-center text-xs text-muted">{t("pull_result_no_pulls")}</div>
            </div>
          )}
        </div>

        {/* Action */}
        {phase === "revealed" || phase === "no_pulls" ? (
          <button
            onClick={availablePulls > 0 && phase === "revealed" ? onPull : onClose}
            className="w-full py-3 text-sm font-bold bg-signal text-background rounded-xl hover:brightness-110 transition-all"
          >
            {availablePulls > 0 && phase === "revealed" ? `🎰 ${t("pull_button")}` : t("dismiss")}
          </button>
        ) : (
          <button
            onClick={onPull}
            disabled={busy || availablePulls <= 0}
            className="w-full py-3 text-sm font-bold bg-signal text-background rounded-xl hover:brightness-110 transition-all disabled:opacity-40"
          >
            {busy ? t("pulling") : `🎰 ${t("pull_button")}`}
          </button>
        )}
      </div>
    </div>,
    document.body
  );
}
