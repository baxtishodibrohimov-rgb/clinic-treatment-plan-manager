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

**Multi-clinic support.** Added after Phase 1–4: an unlimited number of
`Clinic` rows (Settings → Filiallar, SUPER_ADMIN only), each with its own
staff — every `User` (except SUPER_ADMIN, who has none and sees every
clinic) and every `TreatmentPlanCase` belongs to exactly one clinic.
Verified against a real Postgres with two demo clinics ("Bosh filial" /
"2-filial", each with its own doctor + planners, seeded by `app/seed.py`):
a clinic-scoped user's `/api/cases`, `/api/users` and dashboard stats only
ever return their own clinic's rows (confirmed via direct API calls, not
just UI); fetching another clinic's case by id 404s; assigning a case to a
planner from a different clinic 400s; SUPER_ADMIN sees everything and can
scope down via `?clinic_id=` (the frontend's clinic switcher in the
sidebar) or create a clinic-scoped user via `/api/users` (which requires
`clinic_id` unless the new user is itself SUPER_ADMIN). All clinics still
share **one** Cliniccards account — there is no per-clinic API credential.
`app/services/sync_service.py:resolve_clinic_for_appointment` is a
best-effort placeholder (same caveat as the HTTP adapter below) that
matches a `cliniccards_branch_code` configured per clinic against a few
guessed raw-payload field names, falling back to whichever clinic is
marked "standart"; update the field list once real Cliniccards API docs
show what that field is actually called. A database migration
(`08fe781ea38a`) backfills every pre-existing user/case into one
auto-created "Bosh klinika" clinic, so upgrading an already-deployed
single-clinic instance doesn't lose data.

**Phase 5 — Clinical Analysis Wizard (og'iz ichi + profil).** The
questionnaire (33 questions across intraoral-frontal, intraoral-buccal
left/right, and 5 extraoral/profile photo types) was dictated by the
clinic owner and seeded verbatim via migration `970995590f0f` as
`AnalysisTemplate` rows — nothing clinical was invented. `/cases/{id}/analysis`
renders it grouped by photo type, saves answers via
`PUT /api/cases/{id}/analysis-answers/{template_id}`, and includes an
interactive FDI-numbered dental chart (`ToothStatus`, redesigned in
migration `3938cb64131c` to be position-keyed instead of code-keyed):
single click marks a tooth missing, double click toggles primary↔permanent
(or empty↔permanent for positions 6-8, which have no primary variant), and
a "Sut tish / Doimiy tish" button bulk-resets the whole chart — this is
exactly what mixed dentition in children requires. Verified end-to-end
against a real Postgres + a headless-browser run: answers and tooth state
both survive a full page reload. X-ray (OPG/lateral ceph) questions and
Findings/Master-Problem-List generation from these answers are not built
yet — the manual for those hasn't been provided.

**Phases 6–12** are not built — see ARCHITECTURE.md → Phase plan for
what's schema-ready vs. still needed.

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
