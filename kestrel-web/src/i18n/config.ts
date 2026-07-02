export const locales = ["zh-TW", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "zh-TW";
