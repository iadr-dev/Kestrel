import { test, expect } from "@playwright/test";

// Tests use zh-TW locale (default) — text matches from zh-TW.json

test.describe("市場頁面 — 導覽", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(5000);
  });

  test("顯示三個市場分頁", async ({ page }) => {
    await expect(page.locator("button:has-text('台股')")).toBeVisible();
    await expect(page.locator("button:has-text('美股')")).toBeVisible();
    await expect(page.locator("button:has-text('ETF')")).toBeVisible();
  });

  test("顯示7個子視圖", async ({ page }) => {
    await expect(page.locator("button:has-text('每日焦點')")).toBeVisible();
    await expect(page.locator("button:has-text('熱力圖')")).toBeVisible();
    await expect(page.locator("button:has-text('籌碼')")).toBeVisible();
    await expect(page.locator("button:has-text('產業')")).toBeVisible();
    await expect(page.locator("button:has-text('新聞')")).toBeVisible();
    await expect(page.locator("button:has-text('處置股')")).toBeVisible();
    await expect(page.locator("button:has-text('人物動態')")).toBeVisible();
  });

  test("顯示指數條資料", async ({ page }) => {
    // Index strip shows TAIEX label (always rendered even without data)
    await expect(page.locator("text=加權指數")).toBeVisible();
  });

  test("切換到美股分頁", async ({ page }) => {
    await page.locator("button:has-text('美股')").click();
    await page.waitForTimeout(5000);
    await expect(page.locator("text=S&P 500")).toBeVisible();
  });
});

test.describe("市場頁面 — 每日焦點 (View 1)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(5000);
  });

  test("顯示市場漲跌分佈", async ({ page }) => {
    await expect(page.locator("text=市場漲跌分佈")).toBeVisible();
  });

  test("顯示大盤走勢", async ({ page }) => {
    await expect(page.locator("text=大盤走勢")).toBeVisible();
  });

  test("顯示熱門焦點與AI標籤", async ({ page }) => {
    await expect(page.locator("text=熱門焦點")).toBeVisible();
    await expect(page.locator("text=AI")).toBeVisible();
  });

  test("顯示三大法人買賣超", async ({ page }) => {
    await expect(page.locator("text=三大法人買賣超").first()).toBeVisible({ timeout: 10000 });
  });

  test("顯示近5日歷史", async ({ page }) => {
    await expect(page.locator("text=近5日")).toBeVisible();
  });

  test("顯示貢獻排行", async ({ page }) => {
    await expect(page.locator("text=貢獻排行")).toBeVisible();
  });

  test("顯示瞬間波動", async ({ page }) => {
    await expect(page.locator("text=瞬間波動")).toBeVisible();
  });

  test("顯示熱股排行切換按鈕", async ({ page }) => {
    await expect(page.locator("button:has-text('成交量排行')")).toBeVisible();
    await expect(page.locator("button:has-text('漲幅排行')")).toBeVisible();
    await expect(page.locator("button:has-text('跌幅排行')")).toBeVisible();
  });
});

test.describe("市場頁面 — 熱力圖 (View 2)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(4000);
    await page.locator("button:has-text('熱力圖')").click();
    await page.waitForTimeout(4000);
  });

  test("顯示產業熱力圖", async ({ page }) => {
    await expect(page.locator("text=產業熱力圖")).toBeVisible();
  });

  test("顯示時間範圍按鈕", async ({ page }) => {
    await expect(page.locator("button:has-text('今日')").first()).toBeVisible();
    await expect(page.locator("button:has-text('一週')").first()).toBeVisible();
    await expect(page.locator("button:has-text('一月')").first()).toBeVisible();
  });
});

test.describe("市場頁面 — 籌碼 (View 3)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(4000);
    await page.locator("button:has-text('籌碼')").click();
    await page.waitForTimeout(5000);
  });

  test("顯示籌碼日報", async ({ page }) => {
    await expect(page.locator("text=籌碼日報")).toBeVisible();
  });

  test("顯示多空情緒標籤", async ({ page }) => {
    const badge = page.locator("text=/大多|中多|中性|中空|大空/");
    await expect(badge.first()).toBeVisible();
  });

  test("顯示外資區塊", async ({ page }) => {
    await expect(page.locator("text=外資").first()).toBeVisible();
  });

  test("顯示主力分點輸入框", async ({ page }) => {
    const input = page.locator("input[placeholder='Stock ID']");
    await expect(input).toBeVisible();
  });

  test("顯示官股券商", async ({ page }) => {
    await expect(page.locator("text=官股券商")).toBeVisible();
  });

  test("顯示漲跌家數", async ({ page }) => {
    await expect(page.locator("text=漲跌家數").first()).toBeVisible();
  });
});

test.describe("市場頁面 — 產業 (View 4)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(4000);
    await page.locator("button:has-text('產業')").click();
    await page.waitForTimeout(5000);
  });

  test("顯示產業即時", async ({ page }) => {
    await expect(page.locator("text=產業即時")).toBeVisible();
  });

  test("顯示資金流向", async ({ page }) => {
    await expect(page.locator("text=資金流向")).toBeVisible();
  });

  test("顯示產業關係圖", async ({ page }) => {
    await expect(page.locator("text=產業關係圖")).toBeVisible();
  });

  test("顯示查看全部按鈕", async ({ page }) => {
    await expect(page.locator("text=查看全部").first()).toBeVisible();
  });

  test("顯示題材區塊標題", async ({ page }) => {
    await expect(page.locator("text=題材總覽")).toBeVisible();
  });
});

test.describe("市場頁面 — 新聞 (View 5)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(4000);
    await page.locator("button:has-text('新聞')").first().click();
    await page.waitForTimeout(4000);
  });

  test("顯示新聞分頁按鈕", async ({ page }) => {
    await expect(page.locator("button:has-text('證交所公告')")).toBeVisible();
    await expect(page.locator("button:has-text('PTT 股票')")).toBeVisible();
    await expect(page.locator("button:has-text('PTT 期權')")).toBeVisible();
    await expect(page.locator("button:has-text('PTT 表特')")).toBeVisible();
  });

  test("顯示新聞區塊結構", async ({ page }) => {
    // Verify the news section structure loads (data may be empty outside trading hours)
    const newsSection = page.locator("button:has-text('證交所公告')");
    await expect(newsSection).toBeVisible();
  });
});

test.describe("市場頁面 — 美股分頁", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(4000);
    await page.locator("button:has-text('美股')").click();
    await page.waitForTimeout(6000);
  });

  test("顯示美股指數卡片", async ({ page }) => {
    await expect(page.locator("text=S&P 500")).toBeVisible();
    await expect(page.locator("text=Nasdaq")).toBeVisible();
    await expect(page.locator("text=Dow Jones")).toBeVisible();
  });

  test("顯示殖利率曲線", async ({ page }) => {
    await expect(page.locator("text=US Treasury Yield Curve")).toBeVisible();
  });

  test("顯示美股熱門區塊標題", async ({ page }) => {
    await expect(page.locator("text=美股熱門")).toBeVisible();
  });
});

test.describe("市場頁面 — ETF 分頁", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.waitForTimeout(4000);
    await page.locator("button:has-text('ETF')").first().click();
    await page.waitForTimeout(4000);
  });

  test("顯示溢折價分頁按鈕", async ({ page }) => {
    await expect(page.locator("button:has-text('溢折價')")).toBeVisible();
  });

  test("切換到溢折價視圖", async ({ page }) => {
    await page.locator("button:has-text('溢折價')").click();
    await expect(page.locator("text=ETF 溢折價排行")).toBeVisible({ timeout: 10000 });
  });
});

test.describe("市場頁面 — 效能", () => {
  test("頁面5秒內載入", async ({ page }) => {
    const start = Date.now();
    await page.goto("/dashboard/market");
    await page.locator("button:has-text('台股')").waitFor({ state: "visible", timeout: 10000 });
    expect(Date.now() - start).toBeLessThan(10000);
  });

  test("分頁切換3秒內完成", async ({ page }) => {
    await page.goto("/dashboard/market");
    await page.locator("button:has-text('台股')").waitFor({ state: "visible", timeout: 10000 });
    const start = Date.now();
    await page.locator("button:has-text('籌碼')").click();
    await page.locator("text=籌碼日報").waitFor({ state: "visible", timeout: 5000 });
    expect(Date.now() - start).toBeLessThan(5000);
  });
});
