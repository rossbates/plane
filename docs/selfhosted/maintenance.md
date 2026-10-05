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

## Upgrade checklist

1. Review upstream release, dependency/security changes, API contracts and all database migrations.
2. Review Page permissions/sanitization and optimistic concurrency against upstream models.
3. Review Hocuspocus channel names, extension ordering, Redis subscription lifetime and lock coordination. Do not rely on tests alone if the collaboration protocol changes.
4. Review instance config schema and all affected UI components; preference hiding must never weaken permissions/entitlements.
5. Update pinned Node/Python/nginx/Caddy images and JS/Python dependencies together as appropriate. Python constraints must not mask updated direct requirements; a conflict should fail the build rather than silently selecting another version.
6. Run native tests, source builds, public/private policy, and redacted secret scanning. Ensure every application image publishes successfully with the same source SHA. Review SBOMs/security alerts; pinning is not a claim that dependencies have no vulnerabilities.
7. Rehearse against disposable databases/object storage. Check migrations, existing attachments, uploads, collaborative edits and worker tasks.
8. Back up production DB, objects, private Compose and Environment. Choose the immutable release deliberately; preserve volumes/secrets/project names. Roll out through Dokploy and verify.
9. Record release/rollback details privately. Do not downgrade across irreversible migrations without restoring the corresponding data backup.

## Dependency updates

Dependabot opens weekly review PRs for GitHub Actions, Docker bases, npm and pip inputs on the maintained branch. It does not merge, publish from PRs, or deploy. Digest pins and dependency constraints need active maintenance; update and test them, do not freeze vulnerable versions indefinitely. Preserve upstream copyright/license notices and AGPL source availability when distributing modified application images.
