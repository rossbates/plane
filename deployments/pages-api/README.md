# Project Pages API for Plane Community Edition v1.4.2

This fork adds the documented-style API-key-authenticated **project** Pages endpoints to CE. It does not claim to be an official upstream implementation, add paid features, or implement workspace Wiki/Collections. No database migrations or new runtime dependencies are needed.

## Endpoints

Prefix: `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/`

| Method | Suffix | Action |
| --- | --- | --- |
| GET | (none) | Cursor-paginated page metadata |
| POST | (none) | Create a page and its project association atomically |
| GET | `{page_id}/` | Read metadata and HTML body |
| PATCH | `{page_id}/` | Update title, HTML, or supported metadata |
| DELETE | `{page_id}/` | Delete an unlocked, archived page from this project |
| POST | `{page_id}/archive/` | Archive |
| DELETE | `{page_id}/archive/` | Restore |

Use the existing `X-API-Key` authentication and API-key rate limits. Only active workspace/project members have access. Existing Page permission roles and private-page ownership rules apply; restricted guests only see their own pages. Archived projects, foreign-project pages, and soft-deleted associations are excluded. Access/lock changes are owner-only. Deleting a shared page removes only the requested project's association; other projects retain it.

Create requires `name` and `description_html`. Supported metadata: `access` (0 = shared, 1 = private), `color`, `view_props`, `logo_props`, `external_id`, `external_source`, and `is_locked`. Identity, owner, workspace, audit fields, parent, and editor binary/JSON are not client-writable. HTML uses Plane's native size validation and sanitizer. A duplicate non-empty external_id/external_source pair in the project returns 409 on create.

List query parameters: `archived=false` (default), `archived=true`, or `archived=all`; `search`; `per_page`; `cursor`; `fields`. Body content is omitted from lists; fetch the detail endpoint to obtain it. Nested page creation/recursive archive is intentionally not implemented; manage existing nested pages in the UI.

PATCH accepts optional `expected_updated_at` from a previous GET. A stale timestamp returns 409 instead of overwriting a changed page. Locked pages must first be unlocked by their owner; archived pages must first be restored.

## Editor consistency

Full HTML replacement is refused with 409 while a Live/Hocuspocus server subscribes to that page. Close all editor tabs for the page, wait for the disconnect delay, and retry. Metadata updates remain available while editing. Coordination failures return 503 without writing.

The API and existing binary description reads/writes share a Redis lock. The companion fork's Live hook subscribes before loading the database document (stock v1.4.2 subscribes after loading), so new editors must wait for any REST replacement to commit before reading its binary. Existing editors cause the replacement to fail rather than being overwritten. The replacement clears derived binary and JSON; on the next open, official Plane Live converts the sanitized HTML back to its collaborative format. Page transaction processing is scheduled after commit.

Deploy both the custom backend and custom Live images together. This coordination is tied to the pinned v1.4.2 Live image and its `hocuspocus:<page UUID>` Redis channels. Review it on upgrades. Do not expose Redis publicly. Leave REST writes disabled if switching to a different Live protocol without reviewing this mechanism.

## Example

```sh
export PLANE_URL=https://plane.example.com
export WORKSPACE=origin
export PROJECT_ID=your-project-uuid
# PLANE_API_KEY should come from a secret store, not source control.
curl -fsS "$PLANE_URL/api/v1/workspaces/$WORKSPACE/projects/$PROJECT_ID/pages/" \
  -H "X-API-Key: $PLANE_API_KEY" -H 'Content-Type: application/json' \
  -d '{"name":"Operations runbook","description_html":"<h2>Operations</h2><p>Document your system here.</p>"}'
```

## Build and test

From the repository root:

```sh
docker compose -p plane-pages-api-tests -f deployments/pages-api/compose.test.yml \
  up --build --abort-on-container-exit --exit-code-from tests
# This removes ONLY the isolated test stack.
docker compose -p plane-pages-api-tests -f deployments/pages-api/compose.test.yml down -v

docker build --target runtime -f deployments/pages-api/Dockerfile \
  -t plane-backend-local:v1.4.2-pages-api-v1 .
docker build -f deployments/pages-api/Dockerfile.live \
  -t plane-live-local:v1.4.2-pages-api-v1 .
docker run --rm --entrypoint node \
  -v "$PWD/deployments/pages-api/live-coordination.test.mjs:/tmp/live-coordination.test.mjs:ro" \
  plane-live-local:v1.4.2-pages-api-v1 --test /tmp/live-coordination.test.mjs
```

The backend is derived from the exact deployed official v1.4.2 digest, then overlaid with the version-matched fork's Python sources. Runtime dependencies stay unchanged. The local build commands above remain useful for development and emergency rollback. Production pulls the GHCR images described below. Keep every existing volume, credential, environment setting, Compose project name, and frontend/proxy configuration unchanged. Back up the database before deployment. Redeploy through Dokploy.

To roll back while retaining Pages API support, set `PLANE_IMAGE_TAG` to an earlier published `sha-<full commit SHA>` and redeploy. To remove the API extension, restore `makeplane/plane-backend:v1.4.2` for api/worker/beat-worker/migrator and `makeplane/plane-live:v1.4.2` for live, then redeploy. There are no schema changes. Pages created by this API are normal Plane pages and remain usable through the UI after rollback.

## GHCR publishing and Dokploy deployment

The `Fork Pages API` GitHub Actions workflow tests each push, then publishes the backend, Live, and custom frontend on pushes to `selfhost-v1.4.2`. Pull requests only run tests. Manual workflow dispatch is also supported. Publishing uses the short-lived workflow `GITHUB_TOKEN` with `packages:write`; no personal token is committed or required for publishing.

Images:
- `ghcr.io/rossbates/plane-backend`
- `ghcr.io/rossbates/plane-live`
- `ghcr.io/rossbates/plane-frontend`

Each image receives `sha-<full commit SHA>` and the rolling `selfhost-v1.4.2` tag, plus source/revision labels. All three must come from the same completed successful workflow run. The runtime targets exclude pytest/lint dependencies.

New GHCR packages normally start private. For anonymous Dokploy pulls, set each package's visibility to **Public** in its GitHub package settings once. Alternatively, keep packages private and configure a GHCR registry in Dokploy using a securely stored token with `read:packages`; do not put it in Compose, Git, or chat.

In Dokploy's Environment settings set `PLANE_IMAGE_TAG=sha-<full commit SHA>`, then sync `deployments/pages-api/compose.yml` into Dokploy's Raw Compose and redeploy. It uses `pull_policy: always`; api/worker/beat-worker/migrator share the backend image, live uses its paired image, and web uses the custom frontend image. No local Docker builds are required on the deployment host. Pinning one SHA avoids mixed backend/Live releases and makes rollback explicit. If unset, Compose falls back to the rolling branch tag for development.

Publishing is automatic; production deployment is intentionally separate. After pushing code, wait for all publish jobs, select that commit's tag in Dokploy, and redeploy. GitHub Actions does not receive Dokploy credentials or automatically change production.

## Production Compose: source of truth

`deployments/pages-api/compose.yml` on `selfhost-v1.4.2` is the canonical production Compose, **not a generic example or an upstream mirror**. It intentionally follows this owner's preferred self-hosted configuration and may diverge from the official Plane deployment. Make infrastructure changes here, review/commit/push them, then sync the file into Dokploy's Raw Compose. If an emergency edit is made in Dokploy, copy it back into this file promptly to avoid two competing configurations.

Keep secrets, endpoint values, credentials, and the deployed `PLANE_IMAGE_TAG` in Dokploy's Environment settings, outside Git. The Compose should reference those variables. Validate changes with `docker compose --env-file <your-private-env-file> -f deployments/pages-api/compose.yml config --quiet` before deployment; CI also checks it with dummy values. A Compose-only change does not require selecting a newer app image tag unless application code changes too.

### Future S3 storage migration

MinIO remains in the current stack; moving to network RustFS is a separate, deliberate migration. Before removing it:
- Parameterize the relevant backend S3 settings in Compose, then configure the RustFS endpoint, bucket, credentials, region, and TLS settings through Dokploy's Environment.
- Review both backend storage URL behavior and the proxy's `/uploads` routes, which currently point at `plane-ce-minio:9000`. Removing the service alone would leave broken routes.
- Ensure browsers can use the generated upload/download URLs and test uploads, downloads, and existing attachments.
- Copy/verify existing objects before cutting over, and retain the old MinIO volume and a rollback path until verification is complete.

### Existing frontend customizations

`frontend/` contains the reproducible existing custom frontend image: Community badge, GitHub star link, and Billing and Plans sidebar item are hidden. Build it with:

```sh
docker build -t plane-frontend-local:v1.4.2-clean-ui-v4 deployments/pages-api/frontend
```

Dokploy still supplies the domain, TLS routing, and secrets. Do not change the Compose project name or remove its volumes during upgrades. The test stack uses an explicitly isolated subnet to avoid exhausting this host's default Docker pools; override `PLANE_PAGES_TEST_SUBNET` if needed on another host.

Never commit live credentials, database backups, or API keys. The installer keeps these outside this repository.
