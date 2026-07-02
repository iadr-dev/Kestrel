/**
 * Central type barrel. Import shared domain types from `@/types`:
 *
 *   import type { UserPet, StockPrice } from "@/types";
 *
 * Component-local prop interfaces stay co-located with their component — only
 * cross-file / domain shapes belong here.
 */
export type { StockPrice, StockInfo, DailyPriceRow, SnapshotRow, InstRow, FuturesRow, StructureMember, RelationEdge } from "./market";
export type { ChatMessage, AskUserData } from "./chat";
export type { UserPet, ActivePet, PetProgress, PetPullResult } from "./pet";
export type {
  YfHolders,
  YfInsiders,
  YfPeers,
  YfCalendar,
  YfInfo,
} from "./yfinance";
