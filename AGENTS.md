# Agent Development Guide

## Commands

- `pnpm dev` - Start all dev servers (web:3000, admin:3001)
- `pnpm build` - Build all packages and apps
- `pnpm check` - Run all checks (format, lint, types)
- `pnpm check:lint` - OxLint across all packages
- `pnpm check:types` - TypeScript type checking
- `pnpm fix` - Auto-fix format and lint issues
- `pnpm turbo run <command> --filter=<package>` - Target specific package/app
- `pnpm --filter=@plane/ui storybook` - Start Storybook on port 6006

## Code Style

- **Imports**: Use `workspace:*` for internal packages, `catalog:` for external deps
- **TypeScript**: Strict mode enabled, all files must be typed
- **Formatting**: oxfmt, run `pnpm fix:format`
- **Linting**: OxLint with shared `.oxlintrc.json` config
- **Naming**: camelCase for variables/functions, PascalCase for components/types
- **Error Handling**: Use try-catch with proper error types, log errors appropriately
- **State Management**: MobX stores in `packages/shared-state`, reactive patterns
- **Testing**: Tests are optional, targeted tools for this single-user fork—not mandatory release gates. Use existing frameworks when useful; do not introduce test infrastructure for a small repair.
- **Components**: Build in `@plane/ui` with Storybook for isolated development

## Lean self-hosted changes

- Fix the requested problem; do not expand it into release/test infrastructure work without asking.
- Public pushes run lightweight policy/secret checks only. Build/publish manually with `selfhosted.yml`, selecting just the affected component (`frontend` by default). Shared browser changes can select `browser`; select `all` only for a deliberate full upgrade.
- Private image pins may have different source revisions. Change only affected anchors; API/workers/migrator share backend. Backend/Live protocol changes must be reviewed/deployed together.
- Normal loop: edit, build affected component, update its private digest pin, deploy, inspect the affected feature. No application build for docs/Compose-only changes. Back up before schema/storage migrations, not ordinary UI edits.
- Reuse already published images when suitable. No Playwright, full regression runs, or duplicate type-check pass in ordinary publishing.
- If diagnosis or a build exceeds a few minutes, report the blocker/current state rather than silently continuing. Separate immediate recovery from optional follow-up work.

## Backend tests (Docker, optional)

The Django/pytest suite for `apps/api` runs in an isolated stack defined by `docker-compose-test.yml` at the repo root.

Prereq (once): `./setup.sh` — generates `apps/api/.env` from `.env.example`.

- Full suite: `docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests`
- Subset: `docker compose -f docker-compose-test.yml run --rm api-tests pytest -m unit`
- Teardown: `docker compose -f docker-compose-test.yml down -v`

See `apps/api/tests/RUNNING_TESTS.md` for the full walkthrough and troubleshooting; see `apps/api/tests/TESTING_GUIDE.md` for test conventions and fixtures.
