"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { FigureAvatar } from "./FigureAvatar";

interface Figure {
  id: string;
  name_en: string;
  name_zh: string;
  role: string;
  category: string;
  photo_url: string | null;
  associated_stocks: string[];
}

// Matches /figures/events: { id, figure_id, event_type, title, description, date, impact, related_stocks }.
// Figure name/category are not on the event — resolved via the /figures lookup by figure_id.
interface FigureEvent {
  id: string;
  figure_id: string;
  event_type: string;
  title: string;
  description?: string | null;
  date?: string | null;
  impact?: number | null;
  related_stocks?: string[];
}

interface TimelineEvent {
  date?: string | null;
  event_type: string;
  title: string;
  description?: string | null;
  related_stocks?: string[];
  impact?: number | null;
}

type CategoryFilter = "all" | "tech_ceo" | "politician" | "central_bank" | "investor" | "taiwan";

export function FigureEventsTab() {
  const t = useTranslations("market");
  const router = useRouter();
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [selectedFigure, setSelectedFigure] = useState<string | null>(null);
  const [expandedTimeline, setExpandedTimeline] = useState<string | null>(null);

  const { data: figuresData, isLoading: figLoading } = useQuery({
    queryKey: queryKeys.figures.list(),
    queryFn: () => apiFetch<{ data: Figure[] }>("/figures").then(r => r.data || []),
    staleTime: 30 * 60 * 1000,
  });
  const { data: eventsData, isLoading: evtLoading } = useQuery({
    queryKey: queryKeys.figures.events(),
    queryFn: () => apiFetch<{ data: FigureEvent[] }>("/figures/events?limit=50").then(r => r.data || []),
    staleTime: 10 * 60 * 1000,
  });

  const { data: timelineData = [] } = useQuery({
    queryKey: queryKeys.figures.timeline(expandedTimeline),
    queryFn: () => apiFetch<{ data: TimelineEvent[] }>(`/figures/timeline/${expandedTimeline}`).then(r => r.data || []),
    staleTime: 30 * 60 * 1000,
    enabled: !!expandedTimeline,
  });

  const figures = figuresData || [];
  const events = eventsData || [];
  const loading = figLoading || evtLoading;

  const CATEGORIES: { key: CategoryFilter; label: string }[] = [
    { key: "all", label: t("figure_all") },
    { key: "tech_ceo", label: t("figure_tech_ceo") },
    { key: "politician", label: t("figure_politician") },
    { key: "central_bank", label: t("figure_central_bank") },
    { key: "investor", label: t("figure_investor") },
    { key: "taiwan", label: t("figure_taiwan") },
  ];

  // Events carry only figure_id; resolve name/category from the figures list.
  const figureById = new Map(figures.map((f) => [f.id, f]));
  const filteredFigures = category === "all" ? figures : figures.filter(f => f.category === category);
  const filteredEvents = selectedFigure
    ? events.filter(e => e.figure_id === selectedFigure)
    : category === "all"
      ? events
      : events.filter(e => figureById.get(e.figure_id)?.category === category);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex gap-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-9 w-20 animate-shimmer rounded-xl" />)}</div>
        <div className="flex gap-3 overflow-hidden">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-20 w-32 animate-shimmer rounded-xl shrink-0" />)}</div>
        <div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-28 animate-shimmer rounded-xl" />)}</div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => { setCategory(cat.key); setSelectedFigure(null); }}
            className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-colors ${
              category === cat.key
                ? "bg-signal/15 text-signal border border-signal/30"
                : "text-muted hover:text-foreground border border-border/40"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Figure cards (horizontal scroll) */}
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {filteredFigures.map((fig) => (
          <button
            key={fig.id}
            onClick={() => {
              setSelectedFigure(selectedFigure === fig.id ? null : fig.id);
              setExpandedTimeline(expandedTimeline === fig.id ? null : fig.id);
            }}
            className={`shrink-0 w-36 card-atmospheric p-3 text-left transition-all ${
              selectedFigure === fig.id ? "border-signal/50 bg-signal/5" : "hover:border-border"
            }`}
          >
            <div className="flex items-center gap-2 mb-1.5">
              <FigureAvatar figureId={fig.id} nameEn={fig.name_en} nameZh={fig.name_zh} size={32} />
              <div className="min-w-0">
                <div className="text-xs font-bold truncate">{fig.name_zh}</div>
                <div className="text-[10px] text-muted truncate">{fig.name_en}</div>
              </div>
            </div>
            <div className="text-[10px] text-muted truncate">{fig.role}</div>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {fig.associated_stocks.slice(0, 3).map(s => (
                <span key={s} className="text-[9px] px-1 py-0.5 bg-raised rounded font-mono text-signal">{s}</span>
              ))}
              {fig.associated_stocks.length > 3 && (
                <span className="text-[9px] text-muted">+{fig.associated_stocks.length - 3}</span>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Expanded timeline panel */}
      {expandedTimeline && timelineData.length > 0 && (
        <div className="card-atmospheric p-4 border-l-4 border-l-signal">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold">
              {figures.find(f => f.id === expandedTimeline)?.name_zh || ""} — {t("figure_timeline")}
            </span>
            <button
              onClick={() => setExpandedTimeline(null)}
              className="text-[10px] text-muted hover:text-foreground"
            >
              ✕
            </button>
          </div>
          <div className="space-y-2 max-h-[250px] overflow-y-auto">
            {timelineData.map((evt, i) => (
              <div key={i} className="flex items-start gap-3 py-2 border-b border-border/10 last:border-0">
                <div className="shrink-0 w-1.5 h-1.5 rounded-full bg-signal mt-1.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-muted">{evt.date || ""}</span>
                    <span className="text-[9px] px-1.5 py-0.5 bg-raised rounded text-muted">
                      {EVENT_TYPE_ICONS[evt.event_type] || "📋"} {t(`figure_type_${evt.event_type}`)}
                    </span>
                  </div>
                  <p className="text-xs mt-0.5">{evt.title}</p>
                  {(evt.related_stocks?.length ?? 0) > 0 && (
                    <div className="flex gap-1 mt-1">
                      {evt.related_stocks!.slice(0, 5).map(s => (
                        <button key={s} onClick={() => router.push(`/dashboard/stocks/${s}`)} className="text-[9px] px-1 py-0.5 bg-raised rounded font-mono text-signal hover:bg-signal/10">{s}</button>
                      ))}
                    </div>
                  )}
                </div>
                {evt.impact != null && (
                  <span className={`text-[10px] font-mono font-bold shrink-0 ${evt.impact >= 0 ? "text-up" : "text-down"}`}>
                    {evt.impact >= 0 ? "+" : ""}{evt.impact.toFixed(1)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Event timeline */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">{t("figure_timeline")}</h3>
          {selectedFigure && (
            <button
              onClick={() => { setSelectedFigure(null); setExpandedTimeline(null); }}
              className="text-[10px] text-muted hover:text-foreground px-2 py-1 rounded-lg border border-border/40"
            >
              {t("figure_show_all")}
            </button>
          )}
        </div>

        {filteredEvents.length === 0 ? (
          <div className="card-atmospheric p-8 text-center">
            <p className="text-sm text-muted">{t("figure_no_events")}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredEvents.map((evt) => (
              <EventCard key={evt.id} event={evt} figure={figureById.get(evt.figure_id)} onStockClick={(id) => router.push(`/dashboard/stocks/${id}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EventCard({ event, figure, onStockClick }: { event: FigureEvent; figure?: Figure; onStockClick: (id: string) => void }) {
  const t = useTranslations("market");

  const typeIcon = EVENT_TYPE_ICONS[event.event_type] || "📋";
  const figureName = figure?.name_zh || figure?.name_en || "—";
  const stocks = event.related_stocks ?? [];

  return (
    <div className="card-atmospheric p-4 border-l-4 border-l-muted space-y-2">
      {/* Header: figure avatar + event meta */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <FigureAvatar figureId={figure?.id} nameEn={figure?.name_en} nameZh={figure?.name_zh} size={28} />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold">{figureName}</span>
              <span className="text-[10px] px-1.5 py-0.5 bg-raised rounded text-muted">
                {typeIcon} {t(`figure_type_${event.event_type}`)}
              </span>
            </div>
            {event.date && <span className="text-[10px] text-muted font-mono">{event.date}</span>}
          </div>
        </div>
      </div>

      {/* Title + description */}
      <div>
        <h4 className="text-sm font-medium leading-snug">{event.title}</h4>
        {event.description && (
          <p className="text-xs text-muted mt-1 leading-relaxed line-clamp-2">{event.description}</p>
        )}
      </div>

      {/* Impact + related stocks */}
      {(event.impact != null || stocks.length > 0) && (
        <div className="flex items-center justify-between pt-2 border-t border-border/30">
          <div className="flex gap-2">
            {event.impact != null && <ImpactBadge label="1D" value={event.impact} />}
          </div>
          <div className="flex gap-1">
            {stocks.slice(0, 4).map(s => (
              <button
                key={s}
                onClick={(e) => { e.stopPropagation(); onStockClick(s); }}
                className="text-[10px] px-1.5 py-0.5 bg-raised hover:bg-signal/10 rounded font-mono text-signal transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ImpactBadge({ label, value }: { label: string; value: number }) {
  const isPositive = value >= 0;
  return (
    <div className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
      isPositive ? "bg-up/10 text-up" : "bg-down/10 text-down"
    }`}>
      {label} {isPositive ? "+" : ""}{value.toFixed(1)}%
    </div>
  );
}

const EVENT_TYPE_ICONS: Record<string, string> = {
  speech: "🎤",
  trade: "💰",
  policy: "📜",
  product: "🚀",
  legal: "⚖️",
  visit: "✈️",
  filing: "📄",
};
