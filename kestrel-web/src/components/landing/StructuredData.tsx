import { SITE_NAME, SITE_URL, SITE_DESCRIPTION_EN } from "@/lib/constants";

/** JSON-LD structured data for the landing page — the primary GEO/AEO lever.
 *
 *  - Organization + WebSite: declare the brand entity so AI engines (Perplexity,
 *    ChatGPT Search, Google AI Overviews) and search crawlers recognize and can
 *    cite "Kestrel" as a named entity.
 *  - FAQPage: question/answer pairs eligible for featured snippets, People-Also-Ask,
 *    and voice answers (AEO). Answers are concise (~40–60 words) per snippet best
 *    practice.
 *
 *  This is a Server Component (no "use client") — it emits a static <script> tag
 *  into the prerendered HTML where crawlers read it. Rendered once from the landing
 *  page. Kept in English (the schema's machine-readable layer); the visible UI stays
 *  localized via next-intl. */
export function StructuredData() {
  const graph = [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: SITE_NAME,
      url: SITE_URL,
      logo: `${SITE_URL}/logo.png`,
      description: SITE_DESCRIPTION_EN,
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: SITE_NAME,
      url: SITE_URL,
      description: SITE_DESCRIPTION_EN,
      publisher: { "@id": `${SITE_URL}/#organization` },
      inLanguage: ["zh-TW", "en"],
    },
    {
      "@type": "FAQPage",
      "@id": `${SITE_URL}/#faq`,
      // Questions mirror real, high-volume search/answer-engine queries for AI
      // Taiwan-stock tools (bilingual: zh-TW primary + en). Each answer is a
      // self-contained ~40–60-word direct answer for featured-snippet / AI-citation
      // eligibility, leading with "Kestrel" so the entity is unambiguous.
      mainEntity: [
        {
          "@type": "Question",
          name: "Kestrel 是什麼？(What is Kestrel?)",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Kestrel 是一個 AI 驅動的台股與美股分析平台。它整合即時行情、三大法人與籌碼分析、財報基本面，並提供一個能用自然語言回答個股問題的 AI 代理人。Kestrel is an AI-powered analysis platform for the Taiwan (TWSE/TPEx) and US stock markets.",
          },
        },
        {
          "@type": "Question",
          name: "用 AI 分析台股準嗎？(Is AI stock analysis accurate for Taiwan stocks?)",
          acceptedAnswer: {
            "@type": "Answer",
            text: "AI 不能保證獲利或預測漲跌，但能大幅加快研究。Kestrel 的優勢在於它分析的是即時的台股實際數據（股價、法人買賣超、籌碼、營收財報），而非像通用 ChatGPT 只依賴訓練文字，因此結論有真實數據佐證、更可驗證。投資決策與風險仍由使用者自負。",
          },
        },
        {
          "@type": "Question",
          name: "Kestrel 和直接用 ChatGPT 分析股票有什麼不同？(How is Kestrel different from using ChatGPT for stocks?)",
          acceptedAnswer: {
            "@type": "Answer",
            text: "通用型 ChatGPT 懂文字但拿不到即時股市數據，常給出過時或虛構的數字。Kestrel 直接串接台灣證交所、櫃買與 FinMind 的即時資料，AI 回答時會實際查詢當日股價、法人籌碼與財報，所以資訊是最新且可追溯來源的。",
          },
        },
        {
          "@type": "Question",
          name: "Kestrel 是免費的嗎？(Is Kestrel free to use?)",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Kestrel 提供免費方案，可使用 AI 對話與核心台股／美股數據；付費方案則提高用量上限並解鎖更強的 AI 模型。使用 Google 或 LINE 登入即可開始。Kestrel offers a free tier, with paid tiers for higher limits and premium models.",
          },
        },
        {
          "@type": "Question",
          name: "Kestrel 涵蓋哪些市場和數據？(Which markets and data does Kestrel cover?)",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Kestrel 涵蓋台灣上市櫃股票，以及美股與 ETF，整合超過 75 種資料集：每日股價、三大法人買賣超、融資融券、月營收、財務報表、股利與總體經濟指標。It covers Taiwan-listed/OTC stocks plus US equities and ETFs across 75+ datasets.",
          },
        },
        {
          "@type": "Question",
          name: "Kestrel 提供投資建議嗎？(Does Kestrel give financial advice?)",
          acceptedAnswer: {
            "@type": "Answer",
            text: "不提供。Kestrel 是 AI 研究與數據工具，並非持牌投資顧問。所有分析僅供參考，投資決策與其風險由使用者自行承擔。Kestrel is an AI research tool, not a licensed financial advisor; analysis is informational only.",
          },
        },
      ],
    },
  ];

  const jsonLd = { "@context": "https://schema.org", "@graph": graph };

  return (
    <script
      type="application/ld+json"
      // JSON-LD is static, build-time data — safe to inline; no user input.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
