# Maintainable self-hosted Plane platform

This is a source-based fork of Plane Community Edition v1.4.2, maintained on `selfhost-v1.4.2`. Application changes live in their original `apps/` and `packages/` locations. This directory contains only reusable deployment recipes and checks—not copied components, patched bundles, secrets, or a live installation's configuration.

## Architecture and ownership

| Location                                               | Responsibility                                                        |
| ------------------------------------------------------ | --------------------------------------------------------------------- |
| `apps/api/plane/`                                      | Native backend, including project Pages API and runtime UI preference |
| `apps/live/src/`                                       | Native collaborative server, including document coordination          |
| `apps/web/`, `apps/admin/`, `apps/space/`, `packages/` | Actual frontend/shared source                                         |
| `apps/*/Dockerfile.*`                                  | Compile/package those applications from this checkout                 |
| `deployments/selfhosted/compose.example.yml`           | Generic single-user reference, not production source of truth         |
| Separate private deployment checkout                   | Actual Compose, routing, sizing, future RustFS/Postgres choices       |
| Dokploy Environment / protected secret storage         | Credentials, keys, image pin; never Git or build arguments            |

The public fork builds **backend, live, frontend, admin, space, and proxy** images. No Dockerfile uses an official `makeplane/plane-*` application binary as its base, copies generated frontend bundles from source control, or patches a compiled artifact. Node/Python/nginx/Caddy base images are digest-pinned. JavaScript installation uses the frozen pnpm lockfile; injected workspace dependencies and `pnpm deploy --prod` preserve that dependency graph in the Node runtimes. Python's direct and transitive runtime versions are constrained to the original v1.4.2 baseline in `apps/api/requirements/selfhost-constraints.txt`; review that file along with requirements on upgrades. OS security packages still come from Alpine repositories, so builds are dependency-controlled, not claimed to be bit-for-bit reproducible forever.

Backend, Live, Space, web, and admin run as non-root users. Proxy retains the upstream Caddy runtime model. Existing log volumes must be writable by backend UID 10001; inspect ownership before rollout, and never apply permission changes blindly to database or object-storage volumes.

## Public platform changes

- [Project Pages API](../../docs/selfhosted/pages-api.md): API-key CRUD, validation, permissions, optimistic concurrency and coordination with open editors.
- **Runtime promotional UI preference:** set backend `HIDE_PROMOTIONAL_UI=1` to hide the Community badge, GitHub star link, and Billing and Plans menu. `/api/instances/` exposes only the boolean `config.hide_promotional_ui`. Unset/`0` preserves upstream UI; `1`, `true`, or `yes` enables hiding. All deployments use the same source-built frontend. This affects display only: GitHub integrations, permissions, entitlements, and direct billing routes are unchanged. Restart the backend to change the preference; its normal startup clears the instance cache.

## Build and test

From the repository root:

```sh
corepack enable pnpm
pnpm install --frozen-lockfile
pnpm turbo run build --filter=web --filter=admin --filter=space --filter=live
pnpm --filter web test
pnpm --filter live test
python3 deployments/selfhosted/check-policy.py

docker compose -p plane-selfhosted-tests -f deployments/selfhosted/compose.test.yml \
  up --build --abort-on-container-exit --exit-code-from tests
# Removes ONLY the isolated disposable tests, never production volumes.
docker compose -p plane-selfhosted-tests -f deployments/selfhosted/compose.test.yml down -v

docker build --target runtime -f apps/api/Dockerfile.api -t plane-backend:dev apps/api
docker build --target runtime -f apps/live/Dockerfile.live -t plane-live:dev .
docker build --target runtime -f apps/web/Dockerfile.web -t plane-frontend:dev .
docker build --target runtime -f apps/admin/Dockerfile.admin -t plane-admin:dev .
docker build --target runtime -f apps/space/Dockerfile.space -t plane-space:dev .
docker build --target runtime -f apps/proxy/Dockerfile.ce -t plane-proxy:dev apps/proxy
```

The test Compose uses disposable Postgres/Redis with dummy credentials, no host ports, and no production networks/volumes. The subnet is overrideable with `PLANE_PAGES_TEST_SUBNET` if it overlaps an existing network. Native Live tests exercise the actual TypeScript hook, not regex-extracted JavaScript. UI tests render the actual components with both preference values and permission denial.

## CI and registry releases

`.github/workflows/selfhosted.yml` runs lightweight policy checks on push: public/private boundary, redacted Gitleaks scan, and generic Compose validation with dummy values. Image publishing is manual. Dispatch the workflow and choose one component, `browser` for frontend/admin/space, or `all` only for a deliberate full-platform upgrade. Pull requests cannot publish; only manual runs on `selfhost-v1.4.2` can use the job-scoped `packages:write` workflow token. Actions are commit-pinned. Dependency-update PRs are reviewed; they never deploy automatically.

Images: `ghcr.io/<repository-owner>/plane-{backend,live,frontend,admin,space,proxy}`. Published images get `sha-<full commit SHA>` and a rolling branch tag, source/revision labels, provenance, and an SBOM. New packages may require Public visibility for anonymous pulls; otherwise configure a narrowly scoped `read:packages` credential privately in Dokploy. Do not reuse the workflow publishing token on a host.

Production should explicitly pin each application component by immutable tag+digest in private Compose. Components may intentionally run different source revisions; update only the anchors affected by a change. CI publishes images but has **no deployment webhook or production secret access**.

## Private deployment boundary

Copy the example into a separate private repository/check-out **outside this public tree**. That private Compose becomes the installation's configuration source of truth; Dokploy Raw Compose is its synced deployed copy. Commit topology/routing changes privately. Keep even private repositories free of secrets, environment snapshots, backups and uploaded data. Store endpoint addresses and credentials in protected runtime configuration, never image build arguments. Optional `deployments/private/` is ignored by Git and Docker, but a separate checkout is preferred.

Validate privately without printing secrets:

```sh
docker compose --env-file /path/to/protected/deployment.env \
  -f /path/to/private/compose.yml config --quiet
```

The public example is not an instruction to overwrite an existing live Compose. Preserve project names, volume names, unique DNS aliases and existing domain/TLS configuration. Back up Postgres, objects, Compose and Environment before changes. Select the release tag, sync private Compose/Environment to Dokploy, redeploy, and verify API/UI, uploads, editing, background workers, and logs. Browser caches retaining the old patched bundles may need a one-time refresh/service-worker unregister during the source-build transition.

Rollback by restoring the previous private Compose image pins. Do not remove volumes. Future schema changes can make image-only downgrade unsafe: review migration/backup requirements before upgrading.

RustFS and managed Postgres are **future private infrastructure migrations**, not core forks. Changing them requires migrating/verifying objects or database data, reviewing S3 signed URLs and proxy routes or Postgres TLS/dependencies, and retaining the original volumes and rollback path until cutover is verified.

See [fork maintenance](../../docs/selfhosted/maintenance.md) for upstream upgrades and contribution boundaries.
