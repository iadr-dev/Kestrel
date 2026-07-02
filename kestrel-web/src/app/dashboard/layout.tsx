"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { WatchlistPanel } from "@/components/layout/WatchlistPanel";
import { Star } from "lucide-react";
import { isAuthenticated } from "@/lib/auth";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [watchlistOpen, setWatchlistOpen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(300);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Hydration gate: flip to mounted after first client render, then auth-check.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    const startX = e.clientX;
    const startWidth = panelWidth;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = startX - e.clientX;
      const newWidth = Math.min(Math.max(startWidth + delta, 240), 600);
      setPanelWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [panelWidth]);

  if (!mounted || !isAuthenticated()) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="w-6 h-6 border-2 border-signal border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-screen flex overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto relative min-w-0">
        {children}
        {!watchlistOpen && (
          <button
            onClick={() => setWatchlistOpen(true)}
            className="fixed bottom-6 right-6 z-20 p-3 rounded-full bg-surface backdrop-blur-sm hover:bg-raised shadow-lg hover:shadow-xl border border-signal/40 hover:border-signal/70 transition-all"
            title="Watchlist"
          >
            <Star className="w-4 h-4 text-signal" />
          </button>
        )}
      </main>

      {/* Resize handle */}
      {watchlistOpen && (
        <div
          onMouseDown={handleMouseDown}
          className={`w-1.5 shrink-0 cursor-col-resize flex items-center justify-center group hover:bg-signal/10 transition-colors ${
            isDragging ? "bg-signal/20" : ""
          }`}
        >
          <div className={`w-0.5 h-8 rounded-full transition-colors ${
            isDragging ? "bg-signal" : "bg-border group-hover:bg-signal/50"
          }`} />
        </div>
      )}

      {/* Watchlist panel with dynamic width */}
      {watchlistOpen && (
        <div style={{ width: panelWidth }} className="shrink-0 h-full">
          <WatchlistPanel open={watchlistOpen} onClose={() => setWatchlistOpen(false)} />
        </div>
      )}
    </div>
  );
}
