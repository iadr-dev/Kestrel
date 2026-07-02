import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 60000,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "tests/.auth/state.json",
      },
      dependencies: ["setup"],
    },
  ],
  webServer: process.env.CI ? [
    {
      command: "cd ../kestrel-backend && uv run uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "npx next dev --port 3000",
      url: "http://localhost:3000",
      reuseExistingServer: false,
      timeout: 120000,
    },
  ] : undefined,
});
