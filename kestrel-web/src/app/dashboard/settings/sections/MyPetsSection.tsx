"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { PetGachaModal } from "@/components/pets/PetGachaModal";
import type { UserPet, PetProgress, PetPullResult } from "@/types";

type GachaPhase = "idle" | "shaking" | "bursting" | "revealed" | "no_pulls";

const PET_EMOJI: Record<string, string> = {
  sparrow: "🐦", pigeon: "🕊️", robin: "🐤", duckling: "🦆", chick: "🐥",
  hamster: "🐹", bunny: "🐰", kitten: "🐱", owl: "🦉", parrot: "🦜",
  fox: "🦊", penguin: "🐧", corgi: "🐕", hedgehog: "🦔", eagle: "🦅",
  phoenix: "🦅", snow_leopard: "🐆", dragon: "🐉", golden_kestrel: "🦅", cosmic_falcon: "🦅",
};

/** Pet icon. `size` controls the render scale: "sm" (default) for the inline
 *  collection grid / active-pet badge, "lg" for the gacha reveal hero stage.
 *  The default keeps every existing call site byte-for-byte identical. */
function PetIcon({ petId, rarity, size = "sm" }: { petId: string; rarity: string; size?: "sm" | "lg" }) {
  const emoji = PET_EMOJI[petId] || "🐦";
  const lg = size === "lg";
  // Special-pet SVG wrapper + glyph sizes, scaled up for the reveal.
  const wrap = lg ? "w-20 h-20" : "w-6 h-6";
  const svg = lg ? "w-16 h-16" : "w-5 h-5";
  const spark = lg ? "text-base" : "text-[7px]";
  // Plain-emoji font size: text-6xl in the reveal, text-lg in the grid.
  const emojiSize = lg ? "text-6xl" : "text-lg";

  if (petId === "golden_kestrel") {
    return (
      <span className={`relative inline-flex items-center justify-center ${wrap}`}>
        <svg viewBox="0 0 24 24" className={`${svg} drop-shadow-[0_0_6px_rgba(255,215,0,0.9)]`}>
          <path d="M12 2C9.5 2 8 4 8 6c0 1.5.5 2.5 1.5 3.5L6 14l2 1 2-2v4l-2 3h2l2-2 2 2h2l-2-3v-4l2 2 2-1-3.5-4.5C15.5 8.5 16 7.5 16 6c0-2-1.5-4-4-4z" fill="#FFD700" stroke="#B8860B" strokeWidth="0.5"/>
          <circle cx="10.5" cy="5.5" r="0.8" fill="#1a1714"/>
          <path d="M11.5 7l.5.8.5-.8z" fill="#FF6F00"/>
        </svg>
        <span className={`absolute -top-0.5 -right-0.5 ${spark} animate-pulse`}>✨</span>
        <span className="absolute inset-0 rounded-full animate-pulse-slow" style={{boxShadow: "0 0 8px 2px rgba(255,215,0,0.4)"}} />
      </span>
    );
  }
  if (petId === "cosmic_falcon") {
    return (
      <span className={`relative inline-flex items-center justify-center ${wrap}`}>
        <svg viewBox="0 0 24 24" className={`${svg} drop-shadow-[0_0_6px_rgba(139,92,246,0.9)]`}>
          <defs>
            <linearGradient id="cosmic-bird" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#7C3AED"/>
              <stop offset="50%" stopColor="#3B82F6"/>
              <stop offset="100%" stopColor="#06B6D4"/>
            </linearGradient>
          </defs>
          <path d="M12 2C9.5 2 8 4 8 6c0 1.5.5 2.5 1.5 3.5L6 14l2 1 2-2v4l-2 3h2l2-2 2 2h2l-2-3v-4l2 2 2-1-3.5-4.5C15.5 8.5 16 7.5 16 6c0-2-1.5-4-4-4z" fill="url(#cosmic-bird)" stroke="#4C1D95" strokeWidth="0.5"/>
          <circle cx="10.5" cy="5.5" r="0.8" fill="white"/>
          <path d="M11.5 7l.5.8.5-.8z" fill="#C4B5FD"/>
        </svg>
        <span className={`absolute -top-0.5 -right-0.5 ${spark} animate-pulse`}>🌟</span>
        <span className="absolute inset-0 rounded-full animate-pulse-slow" style={{boxShadow: "0 0 8px 2px rgba(139,92,246,0.4)"}} />
      </span>
    );
  }
  if (petId === "phoenix") {
    return (
      <span className={`relative inline-flex items-center justify-center ${wrap}`}>
        <svg viewBox="0 0 24 24" className={`${svg} drop-shadow-[0_0_5px_rgba(255,100,0,0.8)]`}>
          <path d="M12 2C9.5 2 8 4 8 6c0 1.5.5 2.5 1.5 3.5L6 14l2 1 2-2v4l-2 3h2l2-2 2 2h2l-2-3v-4l2 2 2-1-3.5-4.5C15.5 8.5 16 7.5 16 6c0-2-1.5-4-4-4z" fill="#FF4500" stroke="#CC3700" strokeWidth="0.5"/>
          <circle cx="10.5" cy="5.5" r="0.8" fill="#FFF"/>
          <path d="M11.5 7l.5.8.5-.8z" fill="#FFD700"/>
          <path d="M9 16c-1 2-1 3 0 4M15 16c1 2 1 3 0 4M12 17c0 2 0 3 0 4" stroke="#FF6B00" strokeWidth="0.8" fill="none" opacity="0.7"/>
        </svg>
        <span className={`absolute -bottom-0.5 left-1/2 -translate-x-1/2 ${spark} animate-pulse`}>🔥</span>
      </span>
    );
  }
  if (rarity === "rare") {
    return <span className={`${emojiSize} filter drop-shadow-[0_0_3px_rgba(201,162,0,0.5)]`}>{emoji}</span>;
  }
  if (rarity === "uncommon") {
    return <span className={`${emojiSize} filter drop-shadow-[0_0_2px_rgba(255,95,74,0.4)]`}>{emoji}</span>;
  }
  return <span className={emojiSize}>{emoji}</span>;
}

export function MyPetsSection() {
  const petT = useTranslations("pet");
  const [pets, setPets] = useState<UserPet[]>([]);
  const [progress, setProgress] = useState<PetProgress | null>(null);
  const [loading, setLoading] = useState(true);
  // Gacha modal state machine: idle → shaking → bursting → revealed (or no_pulls).
  const [gachaOpen, setGachaOpen] = useState(false);
  const [phase, setPhase] = useState<GachaPhase>("idle");
  const [pullResult, setPullResult] = useState<PetPullResult | null>(null);

  const loadPets = useCallback(async () => {
    try {
      const res = await apiFetch<{ data: UserPet[]; total_available: number }>("/user/pets");
      setPets(res.data || []);
    } catch { /* silent */ }
  }, []);

  const loadProgress = useCallback(async () => {
    try {
      const res = await apiFetch<PetProgress>("/user/pets/progress");
      setProgress(res);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    // Mount fetch: load collection + progress, then clear the loading skeleton.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    Promise.all([loadPets(), loadProgress()]).finally(() => setLoading(false));
  }, [loadPets, loadProgress]);

  const openGacha = () => {
    setPullResult(null);
    setPhase("idle");
    setGachaOpen(true);
  };

  const handlePull = async () => {
    setPullResult(null);
    setPhase("shaking");
    try {
      const res = await apiFetch<PetPullResult>("/user/pets/pull", { method: "POST" });
      if (res.status === "no_pulls") {
        setPullResult(res);
        setPhase("no_pulls");
        return;
      }
      // Gacha juice: shake the box, then burst it open, then reveal. Rarer pulls
      // get a longer shake build-up so the payoff lands harder.
      const rarity = res.pet?.rarity || "common";
      const shakeMs = rarity === "legendary" ? 1700 : rarity === "rare" ? 1300 : 900;
      await new Promise((r) => setTimeout(r, shakeMs));
      setPhase("bursting");
      await new Promise((r) => setTimeout(r, 600)); // matches gift-burst duration
      setPullResult(res);
      setPhase("revealed");
      loadPets();
      loadProgress();
    } catch {
      setPhase("idle");
    }
  };

  const handleEquip = async (recordId: string) => {
    // Optimistic UI update
    setPets((prev) =>
      prev.map((p) => ({ ...p, is_active: p.id === recordId }))
    );
    try {
      const res = await apiFetch<{ status: string }>(`/user/pets/${recordId}/equip`, { method: "PUT" });
      if (res.status !== "equipped") {
        loadPets();
      } else {
        // Notify AgentLogo to refresh
        window.dispatchEvent(new Event("pet-equipped"));
      }
    } catch (e) {
      console.error("Equip failed:", e);
      loadPets();
    }
  };

  const activePet = pets.find((p) => p.is_active);
  const rarityColors: Record<string, string> = { common: "text-muted", uncommon: "text-up", rare: "text-signal", legendary: "text-down" };

  if (loading) return <div className="space-y-3 p-4"><div className="h-6 w-32 bg-raised rounded animate-pulse" /><div className="h-20 bg-raised rounded-2xl animate-pulse" /><div className="grid grid-cols-4 gap-2">{Array.from({length: 8}).map((_,i) => <div key={i} className="h-20 bg-raised rounded-2xl animate-pulse" />)}</div></div>;

  return (
    <div>
      <h2 className="text-lg font-bold mb-2">{petT("title")}</h2>
      <p className="text-xs text-muted mb-6">{petT("subtitle", { count: pets.length })}</p>

      {/* Active pet */}
      {activePet && (
        <div className="mb-6 p-4 border border-border/40 rounded-2xl bg-surface">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-signal/10 flex items-center justify-center text-2xl">
              <PetIcon petId={activePet.pet_id || activePet.id} rarity={activePet.rarity} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold">{activePet.name_zh || activePet.name}</div>
              <div className={`text-[10px] font-medium uppercase ${rarityColors[activePet.rarity] || "text-muted"}`}>{activePet.rarity} · Lv.{activePet.level}</div>
              <div className="text-[10px] text-muted mt-0.5">{activePet.description_zh || activePet.description}</div>
            </div>
          </div>
          {/* XP bar — leveling by playing: the equipped pet gains XP each chat */}
          {activePet.level < 10 ? (
            <div className="mt-3">
              <div className="flex items-center justify-between text-[10px] text-muted mb-1">
                <span>{petT("xp_progress")}</span>
                <span className="font-mono">{activePet.xp}/{activePet.level * 100}</span>
              </div>
              <div className="h-1.5 bg-raised rounded-full overflow-hidden">
                <div
                  className="h-full bg-signal rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, (activePet.xp / (activePet.level * 100)) * 100)}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="mt-3 text-[10px] text-legendary font-bold text-center">★ {petT("level_max")} ★</div>
          )}
        </div>
      )}

      {/* Progress */}
      {progress && (
        <div className="mb-6 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted">{petT("chat_progress")}</span>
            <span className="font-mono">{progress.chat_count}/{progress.next_chat_milestone}</span>
          </div>
          <div className="h-1.5 bg-raised rounded-full overflow-hidden">
            <div className="h-full bg-signal rounded-full" style={{ width: `${(progress.chat_count / progress.next_chat_milestone) * 100}%` }} />
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted">{petT("login_streak")}</span>
            <span className="font-mono">{progress.streak_days}/{progress.next_streak_milestone} {petT("login_streak_days")}</span>
          </div>
          <div className="h-1.5 bg-raised rounded-full overflow-hidden">
            <div className="h-full bg-up rounded-full" style={{ width: `${(progress.streak_days / progress.next_streak_milestone) * 100}%` }} />
          </div>
          {progress.pity_counter > 0 && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted">{petT("pity_label")}</span>
              <span className="font-mono text-legendary">{progress.pity_counter}/{progress.pity_legendary_at}</span>
            </div>
          )}
        </div>
      )}

      {/* Onboarding banner for new users */}
      {pets.length === 0 && (
        <div className="mb-4 p-4 bg-signal/10 border border-signal/30 rounded-2xl">
          <div className="text-sm font-semibold mb-1">{petT("onboarding_title")}</div>
          <p className="text-xs text-muted">{petT("onboarding_desc")}</p>
        </div>
      )}

      {/* Open the gacha modal — the animated gift-box draw lives in PetGachaModal. */}
      <div className="mb-6">
        <button
          onClick={openGacha}
          className="relative px-5 py-2.5 text-sm bg-signal text-background rounded-xl hover:brightness-110 transition-all disabled:opacity-40"
        >
          {`🎰 ${petT("pull_button")} (${petT("available", { count: progress?.available_pulls || 0 })})`}
        </button>
      </div>

      <PetGachaModal
        open={gachaOpen}
        phase={phase}
        result={pullResult}
        availablePulls={progress?.available_pulls || 0}
        petIcon={(petId, rarity) => <PetIcon petId={petId} rarity={rarity} size="lg" />}
        onPull={handlePull}
        onClose={() => setGachaOpen(false)}
      />

      {/* Collection-complete celebration badge (20/20) */}
      {progress?.collection_complete && (
        <div className="mb-4 p-3 rounded-2xl bg-legendary/10 border-2 border-legendary/50 shadow-md shadow-legendary/20 text-center">
          <div className="text-sm font-bold text-legendary">{petT("collection_complete")}</div>
        </div>
      )}

      {/* Collection grid */}
      <div className="grid grid-cols-4 gap-2">
        {pets.map((pet) => {
          const lvlClass = pet.level >= 10
            ? "ring-2 ring-legendary/60 shadow-md shadow-legendary/20"
            : pet.level >= 5
            ? "ring-1 ring-signal/40 shadow-sm shadow-signal/10"
            : "";
          const xpPct = pet.level >= 10 ? 100 : Math.min(100, (pet.xp / (pet.level * 100)) * 100);
          return (
            <button
              key={pet.id}
              onClick={() => handleEquip(pet.id)}
              className={`p-3 rounded-2xl border text-center transition-all ${
                pet.is_active ? "border-signal bg-signal/10" : "border-border/40 hover:border-signal/30"
              } ${lvlClass}`}
            >
              <div className="mb-1"><PetIcon petId={pet.pet_id || pet.id} rarity={pet.rarity} /></div>
              <div className="text-[10px] font-medium truncate">{pet.name_zh || pet.name}</div>
              <div className="flex items-center justify-center gap-1">
                <span className={`text-[9px] ${rarityColors[pet.rarity] || "text-muted"}`}>{pet.rarity}</span>
                <span className="text-[8px] text-signal">Lv.{pet.level}</span>
              </div>
              {/* Per-pet XP bar — shows leveling progress at a glance */}
              <div className="mt-1 h-0.5 bg-raised rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${pet.level >= 10 ? "bg-legendary" : "bg-signal/70"}`}
                  style={{ width: `${xpPct}%` }}
                />
              </div>
              {pet.level >= 10 && <div className="text-[8px] text-legendary font-bold mt-0.5">{petT("level_max")}</div>}
            </button>
          );
        })}
        {Array.from({ length: Math.max(0, 20 - pets.length) }).map((_, i) => (
          <div key={`empty-${i}`} className="p-3 rounded-2xl border border-dashed border-border/30 text-center">
            <div className="text-lg mb-1 opacity-20">❓</div>
            <div className="text-[10px] text-muted/30">???</div>
          </div>
        ))}
      </div>
    </div>
  );
}
