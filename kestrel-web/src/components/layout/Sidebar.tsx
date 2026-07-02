"use client";
import { useTranslations } from "next-intl";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import { useTheme } from "next-themes";
import {
  MessageSquare,
  BarChart3,
  Filter,
  PanelLeftClose,
  Plus,
  Settings,
  LogOut,
  Sun,
  Moon,
  Globe,
  ChevronUp,
  SlidersHorizontal,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";
import { SessionList } from "./SessionList";

const NAV_ITEMS = [
  { href: "/dashboard/chat", icon: MessageSquare, label: "chat" },
  { href: "/dashboard/market", icon: BarChart3, label: "market" },
  { href: "/dashboard/screener", icon: Filter, label: "screener" },
  { href: "/dashboard/settings", icon: SlidersHorizontal, label: "settings" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const t = useTranslations("nav");
  const ta = useTranslations("common.a11y");
  const { theme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [user] = useState<{ display_name?: string; picture_url?: string } | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem("kestrel_user");
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const [activePetEmoji, setActivePetEmoji] = useState<string | null>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Hydration gate (flip after first client render).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
    // Load active pet
    apiFetch<{ data: { pet_id: string } | null }>("/user/pets/active")
      .then((res) => {
        if (res.data) {
          const emojis: Record<string, string> = { sparrow: "🐦", pigeon: "🕊️", robin: "🐤", duckling: "🦆", chick: "🐥", hamster: "🐹", bunny: "🐰", kitten: "🐱", owl: "🦉", parrot: "🦜", fox: "🦊", penguin: "🐧", corgi: "🐕", hedgehog: "🦔", eagle: "🦅", phoenix: "🔥", snow_leopard: "🐆", dragon: "🐉", golden_kestrel: "✨", cosmic_falcon: "🌌" };
          setActivePetEmoji(emojis[res.data.pet_id] || "🦅");
        }
      })
      .catch((err) => logError("Sidebar.loadActivePet", err));
  }, []);

  // Close profile menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <aside className={`${collapsed ? "w-20" : "w-60"} flex flex-col shrink-0 transition-all duration-300 ease-out py-5 px-3`}>
      {/* Logo */}
      <div className={`mb-5 ${collapsed ? "flex justify-center" : "px-2"}`}>
        {collapsed ? (
          <button onClick={() => setCollapsed(false)} className="transition-all hover:scale-105">
            <Image src="/logo.png" alt="Kestrel" width={32} height={32} className="w-8 h-8 rounded-xl" />
          </button>
        ) : (
          <div className="flex items-center justify-between">
            <Link href="/dashboard" className="flex items-center gap-2.5">
              <Image src="/logo.png" alt="Kestrel" width={32} height={32} className="w-8 h-8 rounded-xl" />
              <span className="text-sm font-bold tracking-tight">Kestrel</span>
            </Link>
            <button
              onClick={() => setCollapsed(true)}
              className="p-1.5 rounded-full hover:bg-raised/80 transition-all text-muted"
              aria-label={ta("collapse_sidebar")}
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Nav capsule */}
      <div className={`bg-surface rounded-2xl shadow-sm ${collapsed ? "py-3 px-2" : "py-3 px-2"}`}>
        {/* New chat */}
        <button
          onClick={() => router.push(`/dashboard/chat?new=${Date.now()}`)}
          aria-label={t("new_chat")}
          className={`flex items-center gap-2.5 w-full mb-2 transition-all ${
            collapsed
              ? "justify-center p-2.5 rounded-full hover:bg-raised"
              : "px-3 py-2.5 rounded-xl hover:bg-raised"
          }`}
        >
          <Plus className="w-[18px] h-[18px] text-signal" />
          {!collapsed && <span className="text-sm font-medium">{t("new_chat")}</span>}
        </button>

        {/* Nav items */}
        <nav className={`space-y-1 ${collapsed ? "" : ""}`}>
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? t(item.label) : undefined}
                className={`flex items-center transition-all duration-200 ${
                  collapsed
                    ? "justify-center p-2.5 rounded-full"
                    : "gap-3 px-3 py-2.5 rounded-xl"
                } ${
                  isActive
                    ? collapsed
                      ? "bg-nav-active text-nav-active-text"
                      : "bg-nav-active text-nav-active-text"
                    : "text-muted hover:text-foreground hover:bg-raised/80"
                }`}
              >
                <item.icon className="w-[18px] h-[18px] shrink-0" />
                {!collapsed && <span className="text-sm font-medium">{t(item.label)}</span>}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Recents */}
      {!collapsed && <SessionList />}
      {collapsed && <div className="flex-1" />}

      {/* Profile at bottom */}
      <div ref={profileRef} className={`relative mt-3 ${collapsed ? "flex justify-center" : "px-2"}`}>
        <button
          onClick={() => setProfileOpen(!profileOpen)}
          className={`flex items-center gap-2.5 transition-all ${collapsed ? "p-1" : "w-full px-2 py-2 rounded-2xl hover:bg-surface/80"}`}
        >
          <div className="relative shrink-0">
            {user?.picture_url ? (
              // External OAuth avatar (arbitrary CDN host) — next/image would need each host whitelisted.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={user.picture_url} alt="" referrerPolicy="no-referrer" className="w-9 h-9 rounded-full shadow-sm object-cover" />
            ) : (
              <div className="w-9 h-9 rounded-full bg-signal/20 flex items-center justify-center">
                <span className="text-xs font-bold text-signal">{(user?.display_name || "U")[0]}</span>
              </div>
            )}
            {activePetEmoji && (
              <span className="absolute -bottom-0.5 -right-0.5 text-[10px] bg-surface rounded-full w-4 h-4 flex items-center justify-center shadow-sm">{activePetEmoji}</span>
            )}
          </div>
          {!collapsed && (
            <>
              <span className="text-xs text-foreground/80 truncate flex-1 text-left font-medium">{user?.display_name || "User"}</span>
              <ChevronUp className={`w-3 h-3 text-muted transition-transform ${profileOpen ? "" : "rotate-180"}`} />
            </>
          )}
        </button>

        {/* Profile popup menu */}
        {profileOpen && (
          <div className="absolute bottom-full left-3 right-3 mb-2 bg-surface rounded-2xl shadow-xl shadow-black/10 py-2 z-50">
            <ProfileMenuItem
              icon={mounted && theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              label={mounted ? (theme === "dark" ? t("light_mode") : t("dark_mode")) : ""}
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            />
            <div className="relative group/lang">
              <ProfileMenuItem
                icon={<Globe className="w-4 h-4" />}
                label={t("language")}
                onClick={() => {}}
              />
              <div className="absolute left-full top-0 ml-1 hidden group-hover/lang:block">
                <div className="bg-surface border border-border/40 rounded-2xl shadow-xl py-1.5 w-32">
                  <button onClick={() => { document.cookie = "locale=zh-TW;path=/;max-age=31536000"; window.location.href = window.location.pathname; }} className={`w-full px-3 py-1.5 text-xs text-left hover:bg-raised flex items-center justify-between ${typeof document !== "undefined" && document.cookie.includes("locale=zh-TW") ? "text-signal font-medium" : "text-muted hover:text-foreground"}`}>繁體中文{typeof document !== "undefined" && (document.cookie.includes("locale=zh-TW") || !document.cookie.includes("locale=")) && " ✓"}</button>
                  <button onClick={() => { document.cookie = "locale=en;path=/;max-age=31536000"; window.location.href = window.location.pathname; }} className={`w-full px-3 py-1.5 text-xs text-left hover:bg-raised flex items-center justify-between ${typeof document !== "undefined" && document.cookie.includes("locale=en") ? "text-signal font-medium" : "text-muted hover:text-foreground"}`}>English{typeof document !== "undefined" && document.cookie.includes("locale=en") && " ✓"}</button>
                </div>
              </div>
            </div>
            <ProfileMenuItem
              icon={<Settings className="w-4 h-4" />}
              label={t("settings")}
              href="/dashboard/settings"
            />
            <div className="my-1.5 border-t border-border" />
            <ProfileMenuItem
              icon={<LogOut className="w-4 h-4" />}
              label={t("logout")}
              onClick={() => {
                localStorage.removeItem("kestrel_token");
                localStorage.removeItem("kestrel_user");
                window.location.href = "/login";
              }}
              danger
            />
          </div>
        )}
      </div>
    </aside>
  );
}

function ProfileMenuItem({
  icon,
  label,
  onClick,
  href,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  href?: string;
  danger?: boolean;
}) {
  const cls = `flex items-center gap-3 w-full px-3 py-2 text-sm transition-colors ${
    danger ? "text-down hover:bg-down/10" : "text-muted hover:text-foreground hover:bg-raised"
  }`;

  if (href) {
    return (
      <Link href={href} className={cls}>
        {icon}
        <span>{label}</span>
      </Link>
    );
  }

  return (
    <button onClick={onClick} className={cls}>
      {icon}
      <span>{label}</span>
    </button>
  );
}
