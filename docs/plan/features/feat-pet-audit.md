# Pet System Audit — Bugs, Issues, and Fixes

## System Overview

Gacha-style pet collection where users earn pulls by chatting (1 pull per 50 chats). Equipped pet shows as agent avatar in chat. Purely cosmetic — no gameplay effect on AI responses.

## Critical Bugs — ALL FIXED ✅

### Bug 1: XP Never Resets on Level Up — ✅ FIXED
XP now resets after level up, capped at level 10.

### Bug 2: Admin Pull Consumption — ✅ FIXED
Admins no longer decrement `available_pulls` on pull.

### Bug 3: Race Condition on Equip — ✅ FIXED
Atomic UPDATE: deactivate others + activate target in two separate WHERE clauses. Returns 404 if pet not found.

### Bug 4: Frontend Grid Only Shows 8 Pets — ✅ FIXED
Grid now shows all 20 slots (collected + empty placeholders).

### Bug 5: Silent Error in Chat Counter — ✅ FIXED
Now logs `logger.warning("pet_chat_increment_failed")` with error details.

## Moderate Issues

| # | Issue | Status |
|---|-------|--------|
| 6 | Admin emails hardcoded in source | ✅ FIXED — moved to `config.py` (env-overridable via `ADMIN_EMAILS`) |
| 7 | Equip returns 404 HTTP status | ✅ FIXED — raises HTTPException(404) |
| 8 | Level cap at 10 | ✅ FIXED |
| 9 | No pity system | ✅ FIXED — guaranteed rare at 30 pulls, legendary at 50 pulls (pity_counter resets on rare+ pull) |
| 10 | AgentLogo doesn't refresh after pull/equip | ✅ FIXED — custom event "pet-equipped" dispatched + listened |
| 11 | 4 pets share same 🦅 emoji | ✅ FIXED — PetIcon SVG component with distinct visuals |
| 12 | Login streak wired into auth | ✅ FIXED — OAuth callback updates streak_days + grants pull at 7-day streak |

## Gacha Math

| Rarity | Pets | Weight | Chance per pull |
|--------|------|--------|-----------------|
| Common | 8 | 50 each = 400 | 50% (6.25% each) |
| Uncommon | 6 | 30 each = 180 | 30% (5% each) |
| Rare | 4 | 15 each = 60 | 15% (3.75% each) |
| Legendary | 2 | 5 each = 10 | 5% (2.5% each) |
| **Total pool** | 20 | **650** | 100% |

Wait — the pool is 650 items, not 100. Each pet is repeated by its weight:
- 8 common × 50 = 400
- 6 uncommon × 30 = 180
- 4 rare × 15 = 60
- 2 legendary × 5 = 10
- Total: 650 items in `random.choice()` pool

Actual probabilities: Common=61.5%, Uncommon=27.7%, Rare=9.2%, Legendary=1.5%

**Expected pulls to get first legendary: ~67** (not 20 as previously estimated)
**Expected pulls to get all 20: ~200+**

With earning rate of 1 pull per 50 chats → need ~10,000 chats to complete collection.

## Integration with Agent

- Pet chat count incremented after each agent response (`core.py:112`)
- Active pet displayed as agent avatar in chat (`AgentLogo.tsx`)
- Pet has NO effect on AI behavior (purely cosmetic)
- Pet level/XP have NO gameplay benefit currently

## Potential Enhancement: Pet Personality

Future idea: Pet rarity could influence agent behavior slightly:
- Common pets: Standard responses
- Rare pets: Slightly more detailed analysis
- Legendary pets: Extended thinking enabled, priority API access

Currently NOT implemented — kept for future consideration.

## Missing Flows / Features

### For NEW Users
| Flow | Status | Impact |
|------|--------|--------|
| First-login onboarding (explain pet system) | ✅ DONE | Banner with i18n (`petT("onboarding_title")` / `petT("onboarding_desc")`) |
| Auto-grant first pull visible | ✅ Works | `_ensure_stats()` creates with `available_pulls=1` |
| Empty collection UI | ✅ Works | Shows 20-slot grid with ❓ placeholders |
| Guide to first pull | ✅ DONE | Onboarding banner explains rules + points to pull button (i18n) |

### For EXISTING Users
| Flow | Status | Impact |
|------|--------|--------|
| Chat → earn pulls | ✅ Works | `_increment_pet_chat()` in core.py, grants at 50 chats, logs on grant |
| Pull notification in chat | ✅ DONE | Toast with i18n (`tp("pull_earned")`) via StatusEvent |
| Login streak counting | ✅ DONE | OAuth callback tracks `last_login_date` + `streak_days`, grants pull at 7-day streak |
| Pet level benefit | ✅ DONE | Lv5: ring glow + badge + system prompt bonus; Lv10: gold ring + "MAX" + master-level analysis |
| Pet release/delete | ❌ Future | Not needed for 20 pets |
| AgentLogo refresh after equip | ✅ DONE | Custom event "pet-equipped" dispatched from settings, listened by AgentLogo |

### Authentication
| Flow | Status | Impact |
|------|--------|--------|
| All pet endpoints require auth | ✅ FIXED | `get_current_user_id` raises 401 if no valid token |

### Cross-Feature Integration
| Flow | Status | Impact |
|------|--------|--------|
| Pet in sidebar | ✅ Works | `Sidebar.tsx` loads active pet emoji |
| Pet in chat (AgentLogo) | ✅ Works | Custom SVGs for legendary, emoji for others |
| Pet in settings | ✅ Works | Full collection grid, pull button, progress bars |
| Pet personality affects agent | ✅ DONE | Rarity-based tone injected into system prompt (`_get_pet_personality` in core.py) |
| Pet evolution/upgrade path | ✅ DONE | Level 5: ring glow + Lv badge; Level 10: gold ring + "MAX" label; system prompt bonus at milestones |

## Implementation Status

### Must Fix (Before Release) — ALL DONE ✅
1. ✅ Fix XP reset bug
2. ✅ Fix admin pull consumption
3. ✅ Fix race condition on equip (atomic + 404)
4. ✅ Block anonymous users (401 for unauthenticated)
5. ✅ Wire login streak into auth callback (7-day streak = free pull)

### Should Add (User Engagement) — ALL DONE ✅
6. ✅ Pull earned notification — toast in chat ("恭喜！你獲得了一次抽寵物機會！") via StatusEvent
7. ✅ First-pet onboarding — banner shown when pets.length === 0 ("歡迎來到寵物系統！")
8. ✅ Expand grid to show all 20 slots
9. ✅ AgentLogo refresh after equip — custom event "pet-equipped" dispatched + listened

### Nice to Have (Future)
10. Pet level benefits (visual upgrades at level 5, 10)
11. Pity system (guaranteed rare/legendary after N pulls)
12. Pet personality mode (affects agent tone subtly)

## Files Modified for Fixes

- `kestrel-backend/app/api/v1/endpoints/pets.py` — XP reset, admin bypass, atomic equip, 404 status
- `kestrel-backend/app/models/pet.py` — Move ADMIN_EMAILS to env
- `kestrel-backend/app/agent/core.py` — Add logging to _increment_pet_chat
- `kestrel-web/src/app/dashboard/settings/page.tsx` — Expand grid, add refresh
- `kestrel-web/src/components/chat/AgentLogo.tsx` — Add refetch on equip event
