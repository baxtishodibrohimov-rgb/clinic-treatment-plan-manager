# Clinic Treatment Plan Manager

Turns a Cliniccards "2nd consultation" booking into a tracked, assigned,
deadline-driven treatment-plan case — with Telegram reminders and doctor
review — for a dental/orthodontic clinic.

Stack: **Next.js (frontend) + FastAPI (backend) + PostgreSQL + Redis/Celery**.
See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for the full design and an
honest phase-by-phase status; this README is the run/test guide.

## Quickstart (Docker Compose)

```bash
cp .env.example .env        # edit SECRET_KEY at minimum
docker compose up --build
```

This starts Postgres, Redis, the FastAPI API (`:8000`, runs migrations on
boot), a Celery worker, Celery beat, and the Next.js frontend (`:3000`).
Without `CLINICCARDS_API_URL`/`CLINICCARDS_API_KEY` set, the sync job
automatically uses the built-in mock Cliniccards provider — the app works
end to end with zero external configuration.

Seed demo data (3 planners, 2 doctors, 5 mock patients, 10 cases — one per
status) once the containers are up:

```bash
docker compose exec backend python -m app.seed
```

Then open http://localhost:3000 and log in with `admin@clinic.local` /
`password123` (**change this password before any real deployment** — it's
seed data).

## Running without Docker (what was used to build/verify this)

```bash
# Postgres + Redis running locally, then:
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # adjust DATABASE_URL/REDIS_URL for your local setup
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000

# separately, for background jobs:
.venv/bin/celery -A app.jobs.celery_app worker --loglevel=info
.venv/bin/celery -A app.jobs.celery_app beat --loglevel=info

# frontend, in another terminal:
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev   # http://localhost:3000
```

## How each phase was tested (see ARCHITECTURE.md for what "done" covers)

**Phase 1 — DB, auth, roles.** `alembic upgrade head` applies 25 tables;
`POST /api/auth/login` + `GET /api/auth/me` confirmed working against a
real seeded user, including that a non-admin correctly gets 403 on
admin-only endpoints.

**Phase 2 — Cliniccards sync.** `POST /api/settings/sync-now` (or wait for
the 5-minute Celery beat tick) against the mock adapter: first run creates
5 cases, re-running immediately creates 0 (`cases_created: 0`) — idempotency
confirmed against a real Postgres unique constraint, not just in theory.

**Phase 3 — assignment + dashboard.** `/dashboard` renders a 10-column
Kanban from `GET /api/cases`; `POST /api/cases/{id}/assign` was exercised
against a real case and correctly transitioned `WAITING_ASSIGNMENT →
ASSIGNED` (and straight to `IMAGES_READY` when images were already
complete). Toggling `assignment_config.mode` to `auto` and calling
`app.services.assignment.auto_assign_planner` directly picked the
least-loaded eligible planner, respecting `max_workload`.

**Phase 4 — Telegram + reminders.** Requires `TELEGRAM_BOT_TOKEN` (create a
bot via @BotFather) and a real Telegram user id in a seeded user's
`telegram_id`. Without a token configured, queued notifications correctly
land in the outbox as `failed` with a clear reason instead of crashing —
verified. `run_reminders_task` was run directly against seeded data and
correctly marked overdue cases and queued escalation notifications exactly
once per case (`ReminderSentLog` dedup).

**Phases 5–12** are not built — the case detail page shows exactly what
exists today (patient info, image gallery with required/missing badges,
progress %, assignment, Master Problem List placeholder, audit log) and a
disabled "TAHLILNI BOSHLASH" button explaining the wizard lands in Phase 5.
See ARCHITECTURE.md → Phase plan for what's schema-ready vs. still needed.

## Project structure

```
backend/
  app/
    models/            SQLAlchemy models (25 tables — see ARCHITECTURE.md)
    schemas/            Pydantic request/response DTOs
    services/            case_service, assignment, sync_service, reminders, audit, notifications
    integrations/
      cliniccards/       adapter interface + mock/http providers + factory
      telegram/          Telegram Bot API client
    security/            password hashing, JWT, role-based FastAPI dependencies
    jobs/                Celery app + beat schedule + tasks
    notifications/       message templates + outbox dispatcher
    api/routers/         auth, users, cases, image_types, reminder_rules, settings, webhook
    seed.py              demo data (dev only)
  alembic/versions/      initial schema + reference-data seed migrations
frontend/
  src/
    app/
      login/             login page
      dashboard/         Treatment Planning Dashboard (Kanban)
      cases/[id]/        case detail
      admin/staff/        planner/doctor/consultant role management
      admin/image-types/  required-image-type config
      admin/reminders/    reminder rule config
      admin/settings/     assignment algorithm, sync log, Cliniccards sync trigger
    lib/                 API client, auth context, shared types
    components/shell.tsx  sidebar/nav shell
docker-compose.yml
.env.example
```

## Known limitations (see ARCHITECTURE.md for detail)

- Role checks are endpoint-level, not yet scoped to "a planner's own
  assigned cases only."
- `http_provider.py`'s Cliniccards field mapping is a placeholder pending
  real API docs.
- No automated test suite yet — this build was verified end-to-end
  manually (real Postgres, real Redis, real HTTP requests, a headless
  browser walkthrough of the frontend) rather than with `pytest`, which
  would be the natural next investment.
