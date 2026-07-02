// Maps a news publisher `source` string (zh/en, sometimes noisy) to a locally
// hosted logo under /public/news/<slug>.png. Data-driven: each entry lists the
// substrings that identify the publisher plus its slug. Matching is fuzzy —
// case-insensitive substring match — so variants like "Yahoo股市" / "Yahoo新聞"
// or "財經 – TechNews 科技新報" all resolve to the same logo.

interface SourceLogo {
  slug: string;
  /** Substrings to match against the source name (case-insensitive). */
  patterns: string[];
}

const SOURCE_LOGOS: SourceLogo[] = [
  { slug: "cnyes", patterns: ["anue", "鉅亨", "cnyes"] },
  { slug: "udn", patterns: ["經濟日報", "udn", "聯合"] },
  { slug: "cmoney", patterns: ["cmoney"] },
  { slug: "moneydj", patterns: ["moneydj"] },
  { slug: "yahoo", patterns: ["yahoo"] },
  { slug: "ctee", patterns: ["工商時報", "ctee"] },
  { slug: "ltn", patterns: ["自由財經", "自由時報", "ltn"] },
  { slug: "businesstoday", patterns: ["今周刊", "businesstoday"] },
  { slug: "line", patterns: ["line today", "line"] },
  { slug: "ettoday", patterns: ["ettoday", "財經雲"] },
  { slug: "chinatimes", patterns: ["中時", "chinatimes"] },
  { slug: "moneylink", patterns: ["富聯網", "money-link", "moneylink"] },
  { slug: "sinotrade", patterns: ["sinotrade", "永豐"] },
  { slug: "technews", patterns: ["technews", "科技新報"] },
  { slug: "ithome", patterns: ["ithome"] },
  { slug: "blocktempo", patterns: ["動區", "動趨", "blocktempo"] },
  { slug: "setn", patterns: ["三立", "setn"] },
  { slug: "tvbs", patterns: ["tvbs"] },
];

/**
 * Resolve a publisher `source` name to its local logo path, or null if unknown.
 * @example newsSourceLogo("Anue鉅亨") // "/news/cnyes.png"
 */
export function newsSourceLogo(source: string | null | undefined): string | null {
  if (!source) return null;
  const s = source.toLowerCase();
  for (const { slug, patterns } of SOURCE_LOGOS) {
    if (patterns.some((p) => s.includes(p.toLowerCase()))) {
      return `/news/${slug}.png`;
    }
  }
  return null;
}
