# Academic Schedule Generator

Current state includes:
- Phase 1: Calendar template system and `TimeBlock` generation
- Phase 2: Resource management
- Phase 3: Requirement system
- Phase 4: Greedy scheduler engine
- Phase 5: Weekly schedule visualization (Tkinter)
- Phase 6: Schedule validation/conflict checking
- Auth and roles:
  - `COMPANY`: manage schedule, groups, settings
  - `PERSONAL`: view own schedule

## Run (local)

1. Start PostgreSQL (Docker):
   - `docker compose up -d db`
2. Create/reset schema (recommended after model changes):
   - `python -m app.main --init-only --reset-schema`
3. Start desktop app:
   - `python -m app.main`

## First launch flow

1. App shows bootstrap screen (if no company account exists).
2. Create company admin account.
3. Login and use company dashboard:
   - `Розклад`: periods, subject input, build/validate schedule
   - `Групи`: create groups and personal users
   - `Налаштування`: create default schedule template

### If you see "period not found"

- A period is a date range for which time blocks exist (for example, a semester).
- In company mode, open `Розклад` and click `Швидко створити період`.
- Or open `Налаштування` and create a template with custom dates.

## Tests

- `python -m pytest`

## Docker

Prerequisite: Docker Desktop is running.

- One-click:
  - double-click `run_docker.bat`
- Manual:
  - `docker compose up --build`
- Tests in Docker:
  - `docker compose --profile test up --build tests`
