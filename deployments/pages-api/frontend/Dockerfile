# Upstream Plane CE v1.4.2 frontend pinned to the installed digest.
FROM makeplane/plane-frontend@sha256:22fd2434fb8d6658439f669ab72f999ce0773abe587663da21a77d70bd63ff61
# Hide the Community badge, GitHub star link, and Billing and Plans menu item.
COPY layout-C0Zt7niA.js /usr/share/nginx/html/assets/layout-C0Zt7niA.js
COPY layout-C1wtx7eA.js /usr/share/nginx/html/assets/layout-C1wtx7eA.js
COPY issue.service-CTC2rMYd.js /usr/share/nginx/html/assets/issue.service-CTC2rMYd.js
# HTML-level fallback also hides these exact controls with an old cached bundle.
COPY index.html /usr/share/nginx/html/index.html
COPY README.md /usr/share/doc/plane-local/README.md
COPY edition-badge.tsx /usr/share/doc/plane-local/edition-badge.tsx
COPY star-us-link.tsx /usr/share/doc/plane-local/star-us-link.tsx
COPY workspace-settings.ts /usr/share/doc/plane-local/workspace-settings.ts
