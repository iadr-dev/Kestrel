"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { today as todayStr, daysAgo } from "@/lib/date";

interface ApiResponse<T = unknown> {
  data: T[];
  count: number;
  // Some endpoints add extra top-level fields (summary, trade_date, …).
  [key: string]: unknown;
}

export function useMarketData<T = unknown>(
  path: string,
  params?: Record<string, string>,
  options?: { staleTime?: number; refetchInterval?: number | false }
) {
  const queryString = params
    ? "?" + new URLSearchParams(params).toString()
    : "";

  // Use `null` (a stable primitive) rather than `{}` (a fresh object each render)
  // for the param-less case, so React Query's key stays referentially consistent.
  const queryKey = [path, params ?? null];

  const { data: response, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey,
    queryFn: () => apiFetch<ApiResponse<T>>(`${path}${queryString}`),
    staleTime: options?.staleTime ?? 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    // Opt-in live polling (e.g. realtime snapshot during market hours). Default
    // off so existing callers are unchanged.
    refetchInterval: options?.refetchInterval ?? false,
  });

  return {
    data: response?.data || [] as T[],
    meta: response as (ApiResponse<T> | undefined),
    loading: isLoading,
    error: error ? (error as Error).message : null,
    refetch,
    // Epoch ms when this data was last successfully fetched (React Query) — used by
    // the shared UpdatedAt badge to show "資料更新 YYYY-MM-DD HH:mm:ss" on cron-fed views.
    dataUpdatedAt,
  };
}

export function useStockPrice(stockId: string, days = 60) {
  const start = daysAgo(days);
  return useMarketData(`/stocks/${stockId}/price`, {
    start_date: start,
    end_date: todayStr(),
  });
}
