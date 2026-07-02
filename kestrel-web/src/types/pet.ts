/**
 * Pet / gacha domain types.
 *
 * Previously duplicated across AgentLogo.tsx and settings/page.tsx — kept in
 * one place so the rarity ladder and progression fields stay in sync.
 */

/** A pet the user owns (catalog fields merged with per-user progression). */
export interface UserPet {
  id: string;
  pet_id: string;
  name?: string;
  name_zh?: string;
  description?: string;
  description_zh?: string;
  rarity: string;
  is_active: boolean;
  level: number;
  xp: number;
}

/** The currently-equipped pet, as returned by `/user/pets/active`. */
export interface ActivePet {
  pet_id: string;
  name: string;
  name_zh: string;
  rarity: string;
  level: number;
  xp?: number;
}

/** Pull / streak / collection progress from `/user/pets/progress`. */
export interface PetProgress {
  chat_count: number;
  next_chat_milestone: number;
  streak_days: number;
  next_streak_milestone: number;
  available_pulls: number;
  pity_counter: number;
  pity_legendary_at: number;
  collection_complete: boolean;
}

/** Result of a gacha pull from `/user/pets/pull`. `pet` is present for both
 *  "new" and "duplicate" (the backend returns the selected catalog entry either
 *  way); only absent on "no_pulls". */
export interface PetPullResult {
  status: string;
  pet?: { id: string; name_zh: string; rarity: string };
  xp_gained?: number;
  leveled_up?: boolean;
  new_level?: number;
}
