# Clinic Treatment Plan Manager — Architecture

A standalone system that turns a Cliniccards "2nd consultation" booking into
a tracked, assigned, deadline-driven treatment-plan case with Telegram
reminders and doctor review — built fresh on **Next.js + FastAPI +
PostgreSQL + Redis/Celery**, per the project's own tech requirement.

This is a from-scratch build (not grafted onto another app), so the design
below reflects a clean slate: no legacy schema to reconcile with, no
pre-existing RBAC to extend, no framework constraints inherited from
elsewhere.

## Stack and why

- **Frontend**: Next.js 15 (App Router, TypeScript, Tailwind), a client-side
  SPA-style admin app that talks to the API over JSON. No server components
  hold business logic — the API is the single source of truth, so the same
  backend could serve a different frontend later without change.
- **Backend**: FastAPI (Python), SQLAlchemy 2.0 ORM, Alembic migrations,
  JWT auth (`python-jose` + `passlib[bcrypt]`).
- **Database**: PostgreSQL — real enums for workflow states, JSONB for
  flexible/clinical content, standard foreign keys and unique constraints
  for every invariant the spec asks for (idempotency, one dental-chart per
  case, etc).
- **Background jobs**: Celery + Redis, with `celery beat` driving three
  periodic tasks (Cliniccards sync, reminder/overdue check, notification
  dispatch) — see **Background jobs** below.
- **Telegram**: talks directly to `api.telegram.org` with a bot token (no
  third-party gateway, since this is a fresh project with its own bot).

## Data model

All models live in `backend/app/models/`, one file per entity group. Full
column lists are in the code; this section explains the *shape* and the
decisions behind it.

### Users and roles

Unlike a system that has to reconcile with pre-existing admin/staff tables,
this one has a single `User` table for every login (SUPER_ADMIN, ADMIN,
PLANNER, DOCTOR, CONSULTANT alike) plus a `UserRole(user_id, role)` join
table — a user can hold more than one role. `User.max_workload` is the cap
used by the auto-assignment algorithm. `User.has_role()` treats
SUPER_ADMIN/ADMIN as implicitly holding every role for **authorization**
checks (`app/security/deps.py:require_role`), but code that validates *who
a target user actually is* (e.g. "is this really a planner?" before
assigning a case to them) checks `user.role_names` directly instead —
mixing those two up was an actual bug caught while testing this build (see
`app/api/routers/cases.py:assign`).

### Cliniccards cache, not a Cliniccards mirror

`CliniccardsPatientCache` / `CliniccardsAppointmentCache` are a thin,
denormalized cache of whatever Cliniccards returns — just enough to render
the dashboard and drive case creation without calling Cliniccards on every
page load. Images are **referenced** (`ClinicalImage.external_url`), never
copied, per the spec's explicit instruction not to require mirroring
Cliniccards' media.

### TreatmentPlanCase + state machine (enforced in code, not the DB)

`TreatmentPlanCase.status` is a Postgres enum with the 10 values from spec
section 4. Legal transitions are a plain Python dict
(`app/models/case.py:ALLOWED_TRANSITIONS`), checked by
`app/services/case_service.py:validate_transition` before every status
write. This differs from a database-trigger approach on purpose: every
write to this table already goes through the FastAPI service layer (there
is no direct client-to-database path the way there would be with a
Supabase-style stack), so enforcing the graph in Python is simpler and just
as safe, and the graph is trivial to extend (edit one dict) without a
migration.

Idempotency (spec section 3 — "one appointment never produces two cases")
is a real unique constraint on `cases.cliniccards_appointment_id`, not just
an application-level check, so it holds under concurrent sync runs; see the
`IntegrityError` handling in `case_service.py:ensure_case`.

### The clinical template engine — deliberately empty of clinical rules

`AnalysisTemplate` matches the exact shape the spec asked for
(`template_name, image_type_id, category, question, answer_type, options,
measurement_required, annotation_required, severity, clinical_priority,
presentation_text_template, active`). **No rows describing what to actually
look for on a photo or X-ray exist.** Per the explicit instruction not to
invent clinical rules before the clinic provides its manual, that content
only ever gets entered by an admin (or imported later, Phase 12) —
`Finding.category` / `.severity` are free text for the same reason, not
enums.

### Everything downstream of analysis is schema-ready, UI-pending

Dental chart (`DentalChart` / `ToothStatus`, FDI numbering), Master Problem
List (`Finding`), Treatment Plan Builder (`TreatmentProblem` →
`TreatmentObjective`, `TreatmentPlan` + `TreatmentPlanVersion` for
versioning), Doctor Review (`Review`, the `submit_review` service function),
and Presentation (`Presentation`) all exist today so Phases 5–10 are "build
the UI/generator against this schema," not "design it later under time
pressure." See **Phase plan** below for what's actually wired up.

### Notifications are an outbox, not a direct send

Nothing that assigns or escalates a case calls Telegram directly. Every
notification-worthy event (`case_service.assign_case`, auto-assignment,
reminders, review) only ever **inserts a `Notification` row**
(`status=pending`). A single Celery task
(`app/notifications/dispatcher.py:dispatch_pending`, run every minute) is
the only code that talks to Telegram, formats messages, and marks rows
`sent`/`failed`. A Telegram outage never loses a notification or blocks a
request — it just leaves rows pending for the next run. Verified: with no
`TELEGRAM_BOT_TOKEN` configured, queued notifications correctly land in
`failed` with a clear `TELEGRAM_BOT_TOKEN not configured` error instead of
crashing anything.

### Reminders are config, not code

`ReminderRule` (trigger_type, offset_minutes, notify_roles) is read fresh
every run by `app/services/reminders.py:run_reminders`; changing
"24h/12h/6h/2h" to something else is an admin-panel edit, not a deploy.
`ReminderSentLog` (unique on case+rule) guarantees each rule fires at most
once per case even under a tight Celery beat schedule.

## Cliniccards integration layer

Everything Cliniccards-specific lives under `backend/app/integrations/cliniccards/`:

```
integrations/cliniccards/
  types.py          Dataclasses (CliniccardsPatient, CliniccardsAppointment, ...)
                     — the only contract the rest of the app depends on.
  base.py            CliniccardsAdapter ABC.
  mock_provider.py   MockCliniccardsAdapter — deterministic demo data
                     (5 patients, all with a "2-konsultatsiya" appointment).
  http_provider.py   HttpCliniccardsAdapter — real REST client. Endpoint
                     paths and the API-key header are env-configurable, so
                     no path is hardcoded; only the response *field mapping*
                     (map_patient, map_appointment, ...) is a placeholder,
                     clearly marked, pending real API docs.
  factory.py         get_cliniccards_adapter() — picks Http vs Mock based on
                     whether CLINICCARDS_API_URL/KEY are set.
```

`app/services/sync_service.py:sync_second_consultations` is the single
algorithm behind both intake paths:

- **Poll** (`app/jobs/tasks.py:sync_cliniccards_task`, Celery beat every 5
  minutes) — used when Cliniccards has no webhooks.
- **Webhook** (`POST /api/webhooks/cliniccards`) — accepts a generic
  `{ appointmentId }` envelope (the real payload shape is unknown until
  Cliniccards' docs arrive), behind an optional shared-secret header, and
  re-runs the same sync for just that one appointment.

Both were tested against the mock adapter: a full sync run creates one case
per mock appointment; re-running it immediately after creates zero new
cases (`cases_created: 0`) — confirmed idempotent.

Switching to the real API later: set `CLINICCARDS_API_URL` /
`CLINICCARDS_API_KEY` (+ path overrides if needed), fix the `map_*`
functions in `http_provider.py` to match real payloads. Nothing else should
need to change.

## Background jobs (Celery)

```
app/jobs/celery_app.py   Celery app + beat schedule:
                            - sync_cliniccards_task        every 5 min
                            - dispatch_notifications_task  every 1 min
                            - run_reminders_task            every 5 min
app/jobs/tasks.py        Thin wrappers: open a DB session, call the
                          matching service function, close the session.
```

Run in production as two extra processes alongside the API:
`celery -A app.jobs.celery_app worker` and
`celery -A app.jobs.celery_app beat` (both wired into `docker-compose.yml`).

## RBAC

- `require_admin` / `require_role(*roles)` (`app/security/deps.py`) are
  FastAPI dependencies; SUPER_ADMIN/ADMIN pass every `require_role` check
  automatically.
- Case assignment (`POST /api/cases/{id}/assign`) is admin-only.
- Doctor review (`POST /api/cases/{id}/review`) requires the DOCTOR role
  (or admin) — verified: a planner attempting it gets a 403, a doctor
  succeeds and the case moves to READY/PLAN_IN_PROGRESS correctly.
- Everything else that reads case data just requires being logged in
  (`get_current_user`); there is no per-row RLS layer here since FastAPI
  endpoints are the only way to reach the database — authorization is
  enforced once, at the endpoint, not duplicated at the database layer.

**Known, intentional gap**: endpoint-level role checks aren't yet scoped to
"a planner's own assigned cases only" — any planner/doctor can currently
read/act on any case through `GET/POST /api/cases/*` beyond assignment and
review. Scoping case-level visibility to `responsible_planner_user_id ==
current user` (while doctors keep clinic-wide visibility) is called out as
**Phase 9 — RBAC hardening** rather than rushed into this pass.

## Phase plan (spec section 41)

| Phase | Spec asked for | Status |
|---|---|---|
| 1 | Architecture, DB, login/users | **Done.** Full schema above; JWT login + role-based access. |
| 2 | Cliniccards mock integration + appointment sync | **Done.** Mock adapter, poll + webhook, idempotent case creation — verified live. |
| 3 | TreatmentPlanCase + assignment + dashboard | **Done.** Manual (`POST /assign`) and auto (configurable `least_workload`/`round_robin`) assignment; Kanban dashboard at `/dashboard`. |
| 4 | Telegram notification + reminders | **Done** at the mechanism level (outbox, dispatcher, configurable reminder rules, overdue escalation) — verified via the outbox/failure path; needs a real `TELEGRAM_BOT_TOKEN` to actually deliver messages. |
| 5 | Image gallery + Clinical Analysis Wizard | **Schema + gallery done.** The case page shows images grouped by extraoral/intraoral/radiology with required-missing badges. The guided wizard UI is not built. |
| 6 | Image annotation (Konva/Fabric) | **Not started.** No `ImageAnnotation`-backed canvas UI yet (table exists). |
| 7 | Master Problem List | **Schema + read-only view.** `Finding` renders on the case page; nothing yet auto-populates it (depends on Phase 5/6). |
| 8 | Treatment Plan Builder | **Schema only.** No builder UI. |
| 9 | Doctor review | **Backend done** (`submit_review`, `Review`, role-gated endpoint, verified end to end). No "Send to review" button in the UI yet (needs Phase 8 first). Also where the RLS-equivalent per-planner scoping (above) should land. |
| 10 | PPTX/PDF presentation generator | **Schema only** (`Presentation`). No generator (would use `python-pptx`, per the spec). |
| 11 | Real Cliniccards API | **Adapter ready, not connected.** Swap env vars + fix `http_provider.py` field mapping once real docs exist. |
| 12 | Import the clinical manual's rules | **Blocked on the manual**, by design — see "clinical template engine" above. |

## What was actually verified, not just written

Every claim above that says "verified," "tested," or gives a specific
result came from running the real stack — a local Postgres + Redis, the
FastAPI app under `uvicorn`, the Next.js app under `next build`/`next
start`, and a headless-browser walkthrough (login → dashboard → case detail
→ admin pages) — not from reading the code and assuming it works. Three real
bugs were caught and fixed this way before anything shipped:

1. SQLAlchemy's `Enum` type defaults to a Python enum's `.name` (e.g.
   `"EXTRAORAL"`), not its `.value` (`"extraoral"`) — every enum column
   needed an explicit `values_callable=lambda e: [m.value for m in e]` or
   every enum-typed insert failed. `CaseStatus` happened to hide this (its
   names and values are identical), which is exactly the kind of thing that
   would have shipped silently broken for every *other* enum without a real
   database in the loop.
2. `assign_case` only recomputed image-completion progress at import time,
   so a case whose Cliniccards images were already 100% complete before
   being assigned got stuck at `ASSIGNED` instead of auto-advancing to
   `IMAGES_READY`. Fixed by recomputing progress right after assignment
   too.
3. The case-assignment endpoint validated "is this user a planner?" using
   `User.has_role()`, which treats admins as implicitly holding every role
   — meaning an admin account could have been "assigned" as if it were a
   planner. Fixed to check `Role.PLANNER in user.role_names` directly.

## Things a reviewer should sanity-check before relying on this in production

- The per-case RBAC scoping gap above.
- `http_provider.py`'s field mapping is a placeholder — verify against real
  Cliniccards payloads before flipping `CLINICCARDS_MODE` away from mock.
- `SECRET_KEY` in `.env.example` is a placeholder — generate a real random
  value for any non-local deployment.
- No automated test suite exists yet (all verification this pass was
  manual, end-to-end, against a live stack) — adding `pytest` coverage for
  `case_service.py` and `assignment.py` would be a good next investment
  given how much of the business logic lives there.
