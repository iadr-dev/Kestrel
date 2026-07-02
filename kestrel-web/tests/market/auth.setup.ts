import { test as setup } from "@playwright/test";
import { createHmac } from "crypto";

const JWT_SECRET = "hRUF6DlZnmBU2mbdyP7WU9Ry-W83AY9RMRg00IUuJqEmxqN0kn3cVzvkT_WHLfAu2-7cLaDXhIo9iw7OM_BH4g";

function base64url(data: string): string {
  return Buffer.from(data).toString("base64url");
}

function createJwt(payload: Record<string, unknown>): string {
  const header = base64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = base64url(JSON.stringify(payload));
  const signature = createHmac("sha256", JWT_SECRET)
    .update(`${header}.${body}`)
    .digest("base64url");
  return `${header}.${body}.${signature}`;
}

setup.setTimeout(90000);
setup("authenticate", async ({ page }) => {
  const now = Math.floor(Date.now() / 1000);

  const accessToken = createJwt({
    sub: "playwright-test@kestrel.dev",
    tier: "pro",
    type: "access",
    iat: now,
    exp: now + 3600,
  });

  const refreshToken = createJwt({
    sub: "playwright-test@kestrel.dev",
    tier: "pro",
    type: "refresh",
    iat: now,
    exp: now + 86400 * 7,
  });

  await page.goto("http://localhost:3000");
  await page.evaluate((data) => {
    localStorage.setItem("kestrel_token", data.accessToken);
    localStorage.setItem("kestrel_refresh_token", data.refreshToken);
    localStorage.setItem("kestrel_user", JSON.stringify({
      id: "test-user",
      email: "playwright-test@kestrel.dev",
      display_name: "Playwright Test",
      tier: "pro",
    }));
  }, { accessToken, refreshToken });

  await page.context().storageState({ path: "tests/.auth/state.json" });
});
