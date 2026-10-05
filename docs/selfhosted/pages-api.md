# Project Pages API (Community Edition fork)

This fork adds API-key-authenticated project Pages endpoints to CE. It is not an official upstream implementation, does not enable paid features, and does not implement workspace Wiki/Collections. These changes need no new database migrations or runtime libraries.

Prefix: `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/`

| Method | Suffix               | Action                                         |
| ------ | -------------------- | ---------------------------------------------- |
| GET    | (none)               | Cursor-paginated page metadata                 |
| POST   | (none)               | Create page and project association atomically |
| GET    | `{page_id}/`         | Read metadata and HTML                         |
| PATCH  | `{page_id}/`         | Update title, HTML or supported metadata       |
| DELETE | `{page_id}/`         | Delete an unlocked, archived project page      |
| POST   | `{page_id}/archive/` | Archive                                        |
| DELETE | `{page_id}/archive/` | Restore                                        |

Authenticate with `X-API-Key`; existing API-key rate limits apply. Active workspace/project membership is required. Existing Page roles and private-page ownership apply; restricted guests see only their own pages. Archived projects, foreign-project pages and soft-deleted associations are excluded. Access/lock changes are owner-only. Deleting a shared page removes only this project's association.

Create requires `name` and `description_html`. Supported metadata: `access` (0 shared, 1 private), `color`, `view_props`, `logo_props`, `external_id`, `external_source`, `is_locked`. Owner, identity, workspace, audit fields, parent and editor binary/JSON are not writable. HTML uses native size validation and sanitization. Duplicate non-empty external_id/external_source pairs return 409 on create.

List supports `archived=false` (default), `true` or `all`; `search`, `per_page`, `cursor`, `fields`. Fetch detail for body content. Nested creation/recursive archive are not implemented; manage existing nested pages in the UI.

PATCH accepts `expected_updated_at` from a previous GET. A stale timestamp returns 409. Owners must unlock locked pages first; archived pages must first be restored.

## Collaboration consistency

Full HTML replacement returns 409 while Live subscribes to the page. Close all editor tabs, allow the disconnect delay, and retry. Metadata remains writable. Redis coordination failure returns 503 without writing.

API and editor binary reads/writes share a Redis lock. The native Live Redis extension subscribes **before** database loading; stock v1.4.2 subscribes afterward. A replacement clears derived binary/JSON so Live regenerates collaborative state from sanitized HTML at next open. Page transaction processing is scheduled after commit.

Deploy backend and Live from the same release. This protocol relies on Hocuspocus's `hocuspocus:<page UUID>` channels and extension ordering; review both on upstream upgrades. Redis must stay private. Do not enable replacements with a different Live protocol without reviewing coordination.

```sh
export PLANE_URL=https://plane.example.com
export WORKSPACE=your-workspace
export PROJECT_ID=your-project-uuid
# Load PLANE_API_KEY from protected storage, never source control.
curl -fsS "$PLANE_URL/api/v1/workspaces/$WORKSPACE/projects/$PROJECT_ID/pages/" \
  -H "X-API-Key: $PLANE_API_KEY" -H 'Content-Type: application/json' \
  -d '{"name":"Runbook","description_html":"<h2>Operations</h2><p>System documentation.</p>"}'
```

Native contract tests: `apps/api/plane/tests/contract/api/test_pages.py`. Native Live coordination tests: `apps/live/tests/extensions/redis.test.ts`. Build/test commands and release/rollback procedures: [self-hosted deployment](../../deployments/selfhosted/README.md).
