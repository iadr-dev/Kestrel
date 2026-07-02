/**
 * FinMind `industry_category` is raw Traditional Chinese (e.g. "半導體業").
 * This maps every observed value to an English display name so non-zh locales
 * don't show Chinese industry labels. Used at every direct display site
 * (search results, stock info). Unknown values fall back to the original string.
 *
 * Keys cover both the listed-market form (半導體業) and TPEx/variant spellings
 * (其他電子類, 創新版股票, etc.) seen in /stocks/info/all.
 */
const INDUSTRY_EN: Record<string, string> = {
  // Traditional sectors
  水泥工業: "Cement",
  食品工業: "Food",
  塑膠工業: "Plastics",
  紡織纖維: "Textiles",
  電機機械: "Electric Machinery",
  電器電纜: "Electrical Cable",
  玻璃陶瓷: "Glass/Ceramic",
  造紙工業: "Paper/Pulp",
  鋼鐵工業: "Steel",
  橡膠工業: "Rubber",
  汽車工業: "Automobile",
  建材營造: "Construction",
  航運業: "Shipping",
  觀光事業: "Tourism",
  觀光餐旅: "Tourism/Hospitality",
  金融保險: "Financial",
  金融業: "Financial",
  貿易百貨: "Trading/Retail",
  油電燃氣業: "Oil/Gas/Power",
  化學工業: "Chemical",
  化學生技醫療: "Chemical/Biotech",
  生技醫療業: "Biotech/Medical",
  // Electronics family
  半導體業: "Semiconductor",
  電腦及週邊設備業: "Computer Peripherals",
  光電業: "Optoelectronics",
  通信網路業: "Communications",
  電子零組件業: "Electronic Parts",
  電子通路業: "Electronics Distribution",
  電子商務業: "E-Commerce",
  資訊服務業: "IT Services",
  其他電子業: "Other Electronics",
  其他電子類: "Other Electronics",
  電子工業: "Electronics",
  // Newer / TPEx categories
  文化創意業: "Cultural Creative",
  綠能環保: "Green Energy",
  綠能環保類: "Green Energy",
  數位雲端: "Digital Cloud",
  數位雲端類: "Digital Cloud",
  運動休閒: "Sports/Leisure",
  運動休閒類: "Sports/Leisure",
  居家生活: "Home/Living",
  居家生活類: "Home/Living",
  農業科技: "AgriTech",
  農業科技業: "AgriTech",
  其他: "Other",
  // Fund / index / non-stock instrument types
  ETF: "ETF",
  上櫃ETF: "ETF (TPEx)",
  "上櫃指數股票型基金(ETF)": "ETF (TPEx)",
  ETN: "ETN",
  "指數投資證券(ETN)": "ETN",
  受益證券: "Beneficiary Cert.",
  存託憑證: "Depositary Receipt",
  創新板股票: "Innovation Board",
  創新版股票: "Innovation Board",
  Index: "Index",
  大盤: "Market Index",
  所有證券: "All Securities",
};

/** Localized industry name. zh-TW (default) returns the original Chinese; other
 *  locales return the English mapping (falling back to the original if unknown). */
export function industryName(category: string | undefined | null, locale: string): string {
  if (!category) return "";
  if (locale.startsWith("zh")) return category;
  return INDUSTRY_EN[category] || category;
}
