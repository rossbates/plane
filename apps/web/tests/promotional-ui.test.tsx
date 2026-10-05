/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */
import { renderToStaticMarkup } from "react-dom/server";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  config: undefined as { hide_promotional_ui?: boolean } | undefined,
  allowPermissions: true,
}));
vi.mock("@/hooks/store/use-instance", () => ({ useInstance: () => ({ config: state.config }) }));
vi.mock("@/hooks/store/user", () => ({
  useUserPermissions: () => ({ allowPermissions: () => state.allowPermissions }),
}));
vi.mock("@plane/i18n", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("@/hooks/use-platform-os", () => ({ usePlatformOS: () => ({ isMobile: false }) }));
vi.mock("next-themes", () => ({ useTheme: () => ({ resolvedTheme: "light" }) }));
vi.mock("next/navigation", () => ({ usePathname: () => "/demo/settings/" }));
vi.mock("react-router", () => ({ useParams: () => ({ workspaceSlug: "demo" }) }));
vi.mock("@plane/propel/button", () => ({
  Button: ({ children }: { children: ReactNode }) => <button>{children}</button>,
}));
vi.mock("@plane/propel/tooltip", () => ({ Tooltip: ({ children }: { children: ReactNode }) => <>{children}</> }));
vi.mock("@/components/license/modal/upgrade-modal", () => ({ PaidPlanUpgradeModal: () => null }));
vi.mock("@/components/settings/sidebar/item", () => ({
  SettingsSidebarItem: ({ label }: { label: string }) => <span>{label}</span>,
}));

import { WorkspaceEditionBadge } from "@/components/workspace/edition-badge";
import { StarUsOnGitHubLink } from "../app/(all)/[workspaceSlug]/(projects)/star-us-link";
import { WorkspaceSettingsSidebarItemCategories } from "@/components/settings/workspace/sidebar/item-categories";

beforeEach(() => {
  state.config = undefined;
  state.allowPermissions = true;
});

describe("runtime promotional UI preference", () => {
  it.each([undefined, { hide_promotional_ui: false }])("preserves upstream controls by default: %j", (config) => {
    state.config = config;
    expect(renderToStaticMarkup(<WorkspaceEditionBadge />)).toContain("Community");
    expect(renderToStaticMarkup(<StarUsOnGitHubLink />)).toContain("https://github.com/makeplane/plane");
    expect(renderToStaticMarkup(<WorkspaceSettingsSidebarItemCategories />)).toContain("billing_and_plans");
  });

  it("hides only the three promotional controls when enabled", () => {
    state.config = { hide_promotional_ui: true };
    expect(renderToStaticMarkup(<WorkspaceEditionBadge />)).toBe("");
    expect(renderToStaticMarkup(<StarUsOnGitHubLink />)).toBe("");
    const menu = renderToStaticMarkup(<WorkspaceSettingsSidebarItemCategories />);
    expect(menu).not.toContain("billing_and_plans");
    expect(menu).toContain("general");
  });

  it("never bypasses existing workspace permission checks", () => {
    state.config = { hide_promotional_ui: true };
    state.allowPermissions = false;
    expect(renderToStaticMarkup(<WorkspaceSettingsSidebarItemCategories />)).not.toContain("<span");
  });
});
