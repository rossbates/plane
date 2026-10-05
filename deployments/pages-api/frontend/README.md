# Local Plane frontend customization

Based on Plane Community Edition v1.4.2, AGPL-3.0-only:
https://github.com/makeplane/plane/tree/v1.4.2
License: https://github.com/makeplane/plane/blob/v1.4.2/LICENSE

Two promotional components render null:
- WorkspaceEditionBadge: apps/web/core/components/workspace/edition-badge.tsx
- StarUsOnGitHubLink: apps/web/app/(all)/[workspaceSlug]/(projects)/star-us-link.tsx

Corresponding modified sources are included as edition-badge.tsx and star-us-link.tsx. Their compiled implementations in assets/layout-C0Zt7niA.js and assets/layout-C1wtx7eA.js render null. This removes the Community upgrade badge and the top-right GitHub star link, not licensing checks, paid-feature gating, GitHub integrations, or GitHub issue links. index.html contains narrowly scoped CSS fallbacks for the exact controls, covering browsers with original cached bundles. All upstream legal notices are retained.

The Billing and Plans menu item is also removed from GROUPED_WORKSPACE_SETTINGS, using workspace-settings.ts and the matching compiled list in assets/issue.service-CTC2rMYd.js. Other menu items, route access permissions, and the direct billing URL remain unchanged. A CSS fallback targets only settings-sidebar links to /settings/billing (with or without a trailing slash).

Image: plane-frontend-local:v1.4.2-clean-ui-v4

Build on this host:

```sh
cd /home/ross/.local/share/plane-install/frontend-customization
docker build -t plane-frontend-local:v1.4.2-clean-ui-v4 .
```

The upstream image is pinned to its installed digest. This patch is version-specific; inspect/reapply it when upgrading Plane. The customization survives Dokploy redeployments because Compose references the derived image with pull_policy: never. Rebuild this image before deployment if moving to another host.

To revert, change the web service image back to makeplane/plane-frontend:v1.4.2, remove pull_policy: never, and redeploy. No data migration is involved. Refresh after deployment. If Firefox retains old UI, unregister plane.jwx.io in about:serviceworkers, close all Plane tabs and reopen; this resolved the owner's previously stuck cache without deleting their login.
