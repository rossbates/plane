import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  workers: 1,
  retries: 0,
  timeout: 30000,
  use: {
    baseURL: process.env.PLANE_BROWSER_BASE_URL ?? "http://127.0.0.1:18099",
    browserName: "chromium",
    serviceWorkers: "block",
  },
  reporter: "list",
});
