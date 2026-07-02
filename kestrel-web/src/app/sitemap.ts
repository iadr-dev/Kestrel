import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/constants";

/** /sitemap.xml — the publicly indexable routes. Authenticated /dashboard pages
 *  are intentionally excluded (gated, per-user, not crawlable). */
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      changeFrequency: "daily",
      priority: 1,
      alternates: { languages: { "zh-TW": SITE_URL, en: SITE_URL } },
    },
    {
      url: `${SITE_URL}/login`,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];
}
