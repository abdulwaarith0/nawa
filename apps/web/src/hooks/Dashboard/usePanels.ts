"use client";

import { getApiClient } from "@/lib/apiClient";
import useSWR from "swr";

// ── Applications-by-month chart ──────────────────────────────────────────────
export type ChartRange = "year" | "ytd";

export interface MonthlyPoint {
  // Short month label the backend localizes, or an ISO month the UI formats.
  month: string;
  value: number;
}

const fetchJson = <T>(key: string) => getApiClient().get<T>(key);

// GET /dashboard/applications-by-month?range=year|ytd -> MonthlyPoint[]
export function useApplicationsByMonth(range: ChartRange) {
  const { data, error, isLoading } = useSWR<MonthlyPoint[]>(
    `/dashboard/applications-by-month?range=${range}`,
    fetchJson,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );
  return { points: data ?? null, error, isLoading };
}

// ── Program capacity meters ──────────────────────────────────────────────────
export interface ProgramCapacity {
  program_id: string;
  name_en: string | null;
  name_ar: string | null;
  used: number;
  cap: number;
}

// GET /dashboard/program-capacity -> ProgramCapacity[]
export function useProgramCapacity() {
  const { data, error, isLoading } = useSWR<ProgramCapacity[]>(
    "/dashboard/program-capacity",
    fetchJson,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );
  return { programs: data ?? null, error, isLoading };
}

// ── Calendar ─────────────────────────────────────────────────────────────────
export type CalendarDotKind = "screening" | "interview" | "deadline";

export interface CalendarDay {
  // ISO date (YYYY-MM-DD).
  date: string;
  kinds: CalendarDotKind[];
}

export interface CalendarMonth {
  // ISO month the response covers, e.g. "2026-07".
  month: string;
  today: string | null;
  days: CalendarDay[];
}

// GET /dashboard/calendar?month=YYYY-MM -> CalendarMonth
export function useCalendar(month: string) {
  const { data, error, isLoading } = useSWR<CalendarMonth>(
    `/dashboard/calendar?month=${month}`,
    fetchJson,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );
  return { calendar: data ?? null, error, isLoading };
}
