"use client";

import { useMemo } from "react";

/**
 * Returns the most recent trading date (YYYY-MM-DD) for TWSE.
 *
 * Logic (same as professional TW stock apps):
 * - Weekdays before 9:00 TW time → use previous trading day
 * - Weekends → use last Friday
 * - Weekday during/after market hours → use today
 *
 * This ensures components always show real data instead of "no data".
 */
export function useTradingDate(): string {
  return useMemo(() => getLastTradingDate(), []);
}

export function getLastTradingDate(): string {
  const now = new Date();
  const twOffset = 8 * 60;
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
  const twTime = new Date(utcMs + twOffset * 60000);

  const hour = twTime.getHours();
  const day = twTime.getDay();

  const target = new Date(twTime);

  if (day === 0) {
    // Sunday → last Friday
    target.setDate(target.getDate() - 2);
  } else if (day === 6) {
    // Saturday → last Friday
    target.setDate(target.getDate() - 1);
  } else if (hour < 9) {
    // Weekday before market open → previous trading day
    if (day === 1) {
      // Monday before open → last Friday
      target.setDate(target.getDate() - 3);
    } else {
      target.setDate(target.getDate() - 1);
    }
  }
  // else: weekday 9:00+ → use today

  return target.toISOString().split("T")[0];
}

/**
 * Returns a date N days before the last trading date.
 */
export function getTradingDateRange(daysBack: number): { start: string; end: string } {
  const end = getLastTradingDate();
  const endDate = new Date(end);
  endDate.setDate(endDate.getDate() - daysBack);
  return { start: endDate.toISOString().split("T")[0], end };
}

/**
 * True when the TWSE regular session is open (Mon–Fri, 09:00–13:30 TW time).
 * Used to enable live snapshot polling only while prices actually move.
 */
export function isTwMarketOpen(): boolean {
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
  const tw = new Date(utcMs + 8 * 60 * 60000);
  const day = tw.getDay();
  if (day === 0 || day === 6) return false;
  const minutes = tw.getHours() * 60 + tw.getMinutes();
  return minutes >= 9 * 60 && minutes <= 13 * 60 + 30;
}

/**
 * True when the US regular session is open (Mon–Fri, 09:30–16:00 America/New_York).
 *
 * Uses Intl with the America/New_York timezone so DST (EST↔EDT) is handled
 * automatically — never hardcode a UTC offset for US hours. Parallels
 * isTwMarketOpen(); used to enable live fast-info polling for US surfaces only
 * while prices actually move. Does not account for US market holidays — on a
 * holiday this returns true but fast-info simply yields the last close (the
 * daily fallback already covers that), so no empty state results.
 */
export function isUsMarketOpen(): boolean {
  // Format "now" in New York time and read back the weekday + HH:MM.
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(new Date());

  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  const weekday = get("weekday"); // e.g. "Mon"
  if (weekday === "Sat" || weekday === "Sun") return false;

  // hour12:false can emit "24" for midnight in some engines — normalise to 0.
  const hour = (Number(get("hour")) || 0) % 24;
  const minutes = hour * 60 + (Number(get("minute")) || 0);
  return minutes >= 9 * 60 + 30 && minutes <= 16 * 60;
}
