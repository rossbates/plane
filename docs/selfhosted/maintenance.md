# Maintaining the self-hosted fork

## Upstream baseline

- Upstream: https://github.com/makeplane/plane
- Release: `v1.4.2`
- Commit: `5f7d92784c403f76284f0f16718f320221dc7fec`
- Maintained fork branch: `selfhost-v1.4.2`

Do not blindly merge upstream main into production. The application sources and their lockfiles must stay version-matched. For an upgrade, create a review branch from the next release tag (or consciously merge/rebase that tag), reapply/review the small native changes, update runtime dependency constraints and base-image digests, and run all tests/builds. Keep the baseline above current after a reviewed upgrade.

## Change boundaries

Reusable platform features belong in their native source locations, with native tests:

- Pages REST: API serializers/views/URLs and description coordination utilities.
- Collaboration: Live Redis subscription hook and tests under `apps/live/tests/`.
- UI preference: instance endpoint, shared config type, original React components and `apps/web/tests/`.

Deployment recipes describe how to build/operate the fork. Never introduce parallel copies of core components, committed generated/minified bundles, source-string replacements in compiled output, or private infrastructure settings. Runtime packaging is allowed to copy compiled output **from a source build stage**, not from Git.

Private topology, storage/DB choices, hostnames and endpoint values belong in a private deployment checkout/runtime configuration. Credentials and backups stay outside even that repository. A private Compose-only change usually does not need a new application image.

## Lean release flow

This is a single-user fork. Keep checks available, but do not make every change wait for a full product-style release train.

- Pushes run lightweight public/private-boundary, secret-scan, and generic Compose validation only.
- Publishing is manual from `.github/workflows/selfhosted.yml`; choose one component, `browser` for frontend/admin/space, or `all` only for a deliberate full upgrade.
- Private deployment pins are independent. Update only the affected image anchors with `plane-deployment/select-release.py --components ...`; leave other working components alone.
- Ordinary UI fixes do not require Playwright, full backend tests, or rebuilding backend/Live/proxy. Build the affected image, deploy, and inspect the affected screen.
- Backend schema/storage changes are different: back up first, review migrations, and test more deliberately.

## Translation packaging notes

`@plane/i18n` ships its module tree and authoritative locale JSON together under `dist/`. Keep the dynamic import in `dist/core/instance.js` relative to `dist/locales/`; JSON import attributes also support native Node/SSR loading. Vite normally excludes `node_modules` from dynamic-import expansion, so all three browser applications explicitly allow the pnpm-injected `@plane/i18n` package while continuing to exclude other dependencies.

## Upgrade checklist

1. Review upstream release, dependency/security changes, API contracts and all database migrations.
2. Review Page permissions/sanitization and optimistic concurrency against upstream models.
3. Review Hocuspocus channel names, extension ordering, Redis subscription lifetime and lock coordination. Do not rely on tests alone if the collaboration protocol changes.
4. Review instance config schema and all affected UI components; preference hiding must never weaken permissions/entitlements.
5. Update pinned Node/Python/nginx/Caddy images and JS/Python dependencies together as appropriate. Python constraints must not mask updated direct requirements; a conflict should fail the build rather than silently selecting another version.
6. Run native tests/source builds where useful, plus public/private policy and redacted secret scanning. Publish only the components that changed unless this is a deliberate full-platform upgrade. Review SBOMs/security alerts; pinning is not a claim that dependencies have no vulnerabilities.
7. Rehearse against disposable databases/object storage. Check migrations, existing attachments, uploads, collaborative edits and worker tasks.
8. Back up production DB, objects, private Compose and Environment. Choose the immutable release deliberately; preserve volumes/secrets/project names. Roll out through Dokploy and verify.
9. Record release/rollback details privately. Do not downgrade across irreversible migrations without restoring the corresponding data backup.

## Dependency updates

Dependabot opens weekly review PRs for GitHub Actions, Docker bases, npm and pip inputs on the maintained branch. It does not merge, publish from PRs, or deploy. Digest pins and dependency constraints need active maintenance; update and test them, do not freeze vulnerable versions indefinitely. Preserve upstream copyright/license notices and AGPL source availability when distributing modified application images.
