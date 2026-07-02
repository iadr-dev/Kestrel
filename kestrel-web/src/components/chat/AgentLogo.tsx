"use client";

import { useEffect, useState, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";
import type { ActivePet } from "@/types";

interface Props {
  state: "idle" | "thinking" | "streaming";
  size?: number;
}

const PET_EMOJIS: Record<string, string> = {
  sparrow: "🐦", pigeon: "🕊️", robin: "🐤", duckling: "🦆", chick: "🐥",
  hamster: "🐹", bunny: "🐰", kitten: "🐱", owl: "🦉", parrot: "🦜",
  fox: "🦊", penguin: "🐧", corgi: "🐕", hedgehog: "🦔", eagle: "🦅",
  phoenix: "🦅", snow_leopard: "🐆", dragon: "🐉", golden_kestrel: "🦅", cosmic_falcon: "🦅",
};

const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes

export function AgentLogo({ state, size = 28 }: Props) {
  const [pet, setPet] = useState<ActivePet | null>(null);
  const [sleeping, setSleeping] = useState(false);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadPet = () => {
    apiFetch<{ data: ActivePet | null }>("/user/pets/active")
      .then((res) => { if (res.data) setPet(res.data); })
      .catch((err) => logError("AgentLogo.loadPet", err));
  };

  useEffect(() => {
    loadPet();
    // Listen for pet equip events (dispatched from settings page)
    const handler = () => loadPet();
    window.addEventListener("pet-equipped", handler);
    return () => window.removeEventListener("pet-equipped", handler);
  }, []);

  // Sleeping detection: if idle for 5 minutes, show sleeping state
  useEffect(() => {
    if (state !== "idle") {
      // Reset sleeping when the agent becomes active again (syncing to `state`).
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSleeping(false);
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      return;
    }
    idleTimerRef.current = setTimeout(() => setSleeping(true), IDLE_TIMEOUT);
    return () => { if (idleTimerRef.current) clearTimeout(idleTimerRef.current); };
  }, [state]);

  const petId = pet?.pet_id || "default";
  const isLegendary = pet?.rarity === "legendary";
  const isRare = pet?.rarity === "rare";
  const level = pet?.level || 1;
  const isMaxLevel = level >= 10;
  const isHighLevel = level >= 5;

  // Determine visual state
  const visualState = sleeping ? "sleeping" : state;

  // Level-based glow colors
  const glowColor = isMaxLevel
    ? "rgba(255,216,61,0.4)"
    : isLegendary
    ? "rgba(255,216,61,0.3)"
    : isRare
    ? "rgba(232,116,48,0.3)"
    : isHighLevel
    ? "rgba(94,232,133,0.2)"
    : "transparent";

  return (
    <div
      className={`shrink-0 flex items-center justify-center rounded-full relative ${
        visualState === "thinking" ? "animate-bounce"
        : visualState === "streaming" ? "animate-pulse"
        : visualState === "sleeping" ? ""
        : ""
      }`}
      style={{ width: size, height: size, animationDuration: visualState === "thinking" ? "1s" : "2s" }}
      title={pet ? `${pet.name_zh} (Lv.${pet.level})` : "Kestrel"}
    >
      {/* Level 10 MAX: animated sparkle ring */}
      {isMaxLevel && visualState !== "sleeping" && (
        <div
          className="absolute inset-[-3px] rounded-full animate-spin"
          style={{
            animationDuration: "4s",
            background: "conic-gradient(from 0deg, transparent, rgba(255,216,61,0.4), transparent, rgba(255,216,61,0.2), transparent)",
          }}
        />
      )}

      {/* Level 5+: glow ring */}
      {isHighLevel && !isMaxLevel && visualState !== "sleeping" && (
        <div
          className="absolute inset-[-2px] rounded-full animate-pulse"
          style={{ boxShadow: `0 0 8px 2px ${glowColor}`, animationDuration: "3s" }}
        />
      )}

      {/* Legendary glow (always if legendary, regardless of level) */}
      {isLegendary && !isMaxLevel && visualState !== "sleeping" && (
        <div className="absolute inset-0 rounded-full" style={{ boxShadow: "0 0 8px 2px rgba(255,216,61,0.3)" }} />
      )}

      {/* Pet SVG or emoji */}
      {petId === "golden_kestrel" ? (
        <GoldenKestrelSVG size={size} state={visualState} />
      ) : petId === "cosmic_falcon" ? (
        <CosmicFalconSVG size={size} state={visualState} />
      ) : petId === "owl" ? (
        <OwlSVG size={size} state={visualState} />
      ) : petId === "fox" ? (
        <FoxSVG size={size} state={visualState} />
      ) : (
        <span className={`${size >= 32 ? "text-xl" : "text-base"} select-none ${visualState === "sleeping" ? "opacity-50" : ""}`}>
          {sleeping ? "💤" : (PET_EMOJIS[petId] || "🦅")}
        </span>
      )}

      {/* Max level sparkle particles */}
      {isMaxLevel && visualState !== "sleeping" && (
        <>
          <span className="absolute -top-0.5 -right-0.5 text-[6px] animate-ping" style={{ animationDuration: "2s" }}>✦</span>
          <span className="absolute -bottom-0.5 -left-0.5 text-[6px] animate-ping" style={{ animationDuration: "2.5s", animationDelay: "0.7s" }}>✦</span>
        </>
      )}

      {/* High level subtle sparkle */}
      {isHighLevel && !isMaxLevel && visualState !== "sleeping" && (
        <span className="absolute -top-0.5 -right-0.5 text-[5px] animate-pulse" style={{ animationDuration: "3s" }}>·</span>
      )}

      {/* Sleeping zzz indicator */}
      {sleeping && (
        <span className="absolute -top-1 -right-1 text-[8px] animate-float">💤</span>
      )}
    </div>
  );
}

// === Individual Pet SVG Animations ===

function GoldenKestrelSVG({ size, state }: { size: number; state: string }) {
  const s = size * 0.8;
  return (
    <svg viewBox="0 0 32 32" width={s} height={s} className={state === "sleeping" ? "opacity-50" : ""}>
      {/* Body */}
      <ellipse cx="16" cy="18" rx="7" ry="9" fill="#FFD700" opacity="0.9" />
      {/* Head */}
      <circle cx="16" cy="9" r="6" fill="#FFC107" />
      {/* Eyes */}
      {state === "sleeping" ? (
        <>
          <path d="M13 8 L15 9" stroke="#5D4037" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M17 8 L19 9" stroke="#5D4037" strokeWidth="1.5" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="14" cy="8" r="1.5" fill="#1a1714" />
          <circle cx="18" cy="8" r="1.5" fill="#1a1714" />
          <circle cx="14.5" cy="7.5" r="0.5" fill="white" />
          <circle cx="18.5" cy="7.5" r="0.5" fill="white" />
        </>
      )}
      {/* Beak */}
      <path d="M15 11 L16 13 L17 11 Z" fill="#FF6F00" />
      {/* Wings */}
      <ellipse cx="10" cy="17" rx="3" ry="6" fill="#FFA000" className={state === "thinking" ? "animate-wing-left" : ""} />
      <ellipse cx="22" cy="17" rx="3" ry="6" fill="#FFA000" className={state === "thinking" ? "animate-wing-right" : ""} />
      {/* Crown sparkle */}
      <path d="M14 3 L16 1 L18 3" stroke="#FFD700" strokeWidth="1" fill="none" strokeLinecap="round" />
      <circle cx="16" cy="1" r="0.8" fill="#FFD700" />
    </svg>
  );
}

function CosmicFalconSVG({ size, state }: { size: number; state: string }) {
  const s = size * 0.8;
  return (
    <svg viewBox="0 0 32 32" width={s} height={s} className={state === "sleeping" ? "opacity-50" : ""}>
      {/* Cosmic glow */}
      <circle cx="16" cy="16" r="14" fill="url(#cosmic-grad)" opacity="0.3" />
      <defs>
        <radialGradient id="cosmic-grad"><stop offset="0%" stopColor="#8B5CF6" /><stop offset="100%" stopColor="transparent" /></radialGradient>
      </defs>
      {/* Body */}
      <ellipse cx="16" cy="18" rx="6" ry="8" fill="#6D28D9" />
      {/* Head */}
      <circle cx="16" cy="9" r="5.5" fill="#7C3AED" />
      {/* Eyes */}
      {state === "sleeping" ? (
        <path d="M13 8.5 Q16 10 19 8.5" stroke="white" strokeWidth="1" fill="none" />
      ) : (
        <>
          <circle cx="14" cy="8.5" r="2" fill="white" opacity="0.9" />
          <circle cx="18" cy="8.5" r="2" fill="white" opacity="0.9" />
          <circle cx="14" cy="8.5" r="1" fill="#1a1714" />
          <circle cx="18" cy="8.5" r="1" fill="#1a1714" />
        </>
      )}
      {/* Stars around */}
      <circle cx="5" cy="5" r="0.8" fill="white" className="animate-pulse" />
      <circle cx="27" cy="7" r="0.6" fill="white" className="animate-pulse" style={{animationDelay:"0.5s"}} />
      <circle cx="3" cy="22" r="0.5" fill="white" className="animate-pulse" style={{animationDelay:"1s"}} />
      <circle cx="28" cy="25" r="0.7" fill="white" className="animate-pulse" style={{animationDelay:"1.5s"}} />
    </svg>
  );
}

function OwlSVG({ size, state }: { size: number; state: string }) {
  const s = size * 0.8;
  return (
    <svg viewBox="0 0 32 32" width={s} height={s} className={state === "sleeping" ? "opacity-50" : ""}>
      {/* Body */}
      <ellipse cx="16" cy="20" rx="8" ry="10" fill="#8D6E63" />
      {/* Belly */}
      <ellipse cx="16" cy="22" rx="5" ry="7" fill="#D7CCC8" />
      {/* Head */}
      <circle cx="16" cy="10" r="7" fill="#795548" />
      {/* Face disc */}
      <circle cx="16" cy="11" r="5" fill="#EFEBE9" />
      {/* Eyes */}
      {state === "sleeping" ? (
        <>
          <path d="M12 10 Q13 11 14 10" stroke="#3E2723" strokeWidth="1.5" fill="none" />
          <path d="M18 10 Q19 11 20 10" stroke="#3E2723" strokeWidth="1.5" fill="none" />
        </>
      ) : (
        <>
          <circle cx="13" cy="10" r="2.5" fill="#FFC107" />
          <circle cx="19" cy="10" r="2.5" fill="#FFC107" />
          <circle cx="13" cy="10" r="1.5" fill="#1a1714" />
          <circle cx="19" cy="10" r="1.5" fill="#1a1714" />
        </>
      )}
      {/* Beak */}
      <path d="M15 13 L16 15 L17 13 Z" fill="#FF8F00" />
      {/* Ear tufts */}
      <path d="M10 5 L11 3 L12 6" fill="#5D4037" />
      <path d="M20 5 L21 3 L22 6" fill="#5D4037" />
    </svg>
  );
}

function FoxSVG({ size, state }: { size: number; state: string }) {
  const s = size * 0.8;
  return (
    <svg viewBox="0 0 32 32" width={s} height={s} className={state === "sleeping" ? "opacity-50" : ""}>
      {/* Body */}
      <ellipse cx="16" cy="20" rx="7" ry="9" fill="#E65100" />
      {/* Belly */}
      <ellipse cx="16" cy="22" rx="4" ry="6" fill="#FFF3E0" />
      {/* Head */}
      <circle cx="16" cy="10" r="6.5" fill="#FF6D00" />
      {/* Ears */}
      <polygon points="10,5 12,1 14,6" fill="#FF6D00" />
      <polygon points="18,6 20,1 22,5" fill="#FF6D00" />
      <polygon points="11,4.5 12,2 13,5.5" fill="#FFF3E0" />
      <polygon points="19,5.5 20,2 21,4.5" fill="#FFF3E0" />
      {/* Eyes */}
      {state === "sleeping" ? (
        <>
          <path d="M13 9.5 L15 10.5" stroke="#3E2723" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M17 10.5 L19 9.5" stroke="#3E2723" strokeWidth="1.5" strokeLinecap="round" />
        </>
      ) : (
        <>
          <ellipse cx="13.5" cy="9.5" rx="1.5" ry="2" fill="#1a1714" />
          <ellipse cx="18.5" cy="9.5" rx="1.5" ry="2" fill="#1a1714" />
          <circle cx="13" cy="9" r="0.5" fill="white" />
          <circle cx="18" cy="9" r="0.5" fill="white" />
        </>
      )}
      {/* Nose */}
      <circle cx="16" cy="12" r="1.2" fill="#1a1714" />
      {/* Tail */}
      <path d="M22 22 Q28 18 26 14" stroke="#FF6D00" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M26 14 Q25 13 26 12" stroke="#FFF3E0" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  );
}
