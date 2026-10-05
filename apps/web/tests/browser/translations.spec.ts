/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */
import { expect, test } from "@playwright/test";

// The real production frontend and its translation resources are not mocked.
// Only unauthenticated API state is simulated; no production account is used.
for (const [language, expected, continueLabel] of [
  ["en", "New to Plane?", "Continue"],
  ["fr", "Nouveau sur Plane ?", "Continuer"],
] as const) {
  test(`source-built sign-in renders ${language} translations`, async ({ page }) => {
    const failedTranslationAssets: string[] = [];
    page.on("requestfailed", (request) => {
      if (/\/(?:auth|common)-[^/]+\.js$|\/locales\//.test(request.url())) {
        failedTranslationAssets.push(request.url());
      }
    });
    await page.addInitScript((locale) => localStorage.setItem("userLanguage", locale), language);
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/instances/") {
        await route.fulfill({
          json: {
            instance: {
              id: "browser-test-instance",
              is_setup_done: true,
              is_activated: true,
              current_version: "1.4.2",
            },
            config: {
              enable_signup: true,
              is_email_password_enabled: true,
              is_magic_login_enabled: false,
              is_self_managed: true,
              hide_promotional_ui: true,
            },
          },
        });
      } else {
        await route.fulfill({ status: 401, json: { error: "Authentication required" } });
      }
    });
    await page.goto("/");
    await expect(page.getByText(expected, { exact: true })).toBeVisible();
    await expect(page.getByText("auth.common.new_to_plane", { exact: true })).toHaveCount(0);
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.getByRole("button", { name: continueLabel, exact: true })).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/\b(?:auth|common)\.[a-z_.]+/);
    expect(failedTranslationAssets).toEqual([]);
  });
}
