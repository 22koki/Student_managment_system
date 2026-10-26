# ✳ NOVA Campus — Student Intelligence, Beautifully Simple

> **Internship Task 2 — Student Management System**  
> A working full-stack student records platform, designed to feel like real campus software rather than a CRUD tutorial.

**Live features:** Student creation · Profile details · Updating · Deletion with confirmation · Search · Filtering · Pagination · Sorting · CSV export · Student wellness indicators · Enrollment analytics · Change history · API documentation · Automated backend integration tests.

## What makes NOVA different?

NOVA gives a campus team two connected lenses: **the student directory** (accurate, editable records) and **the campus pulse** (an instant understanding of who is learning, how enrollment is changing, and who may need support).

It has a custom responsive interface, keyboard-friendly forms, contextual confirmations and alerts, informative empty states, a distinct lavender/navy visual identity, and synthetic sample records to demonstrate all key flows.

The wellbeing/watchlist indicator is a **simple rule**, not a medical or academic prediction. It flags *active* students with GPA below 2.0 or attendance below 75% for a human check-in. It never makes an automated enrollment decision.

## Run locally

Requires **Python 3.10+**. No frontend build step, npm installation, or external database service is required.

```bash
git clone https://github.com/22koki/Student_managment_system.git
cd Student_managment_system
python -m venv .venv
```

Activate the virtual environment:

- Windows PowerShell: ` .venv\Scripts\Activate.ps1 ` (or use `.venv\Scripts\python.exe` directly)
- macOS/Linux: `source .venv/bin/activate`

Install and run:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload
```

**Open:** http://127.0.0.1:8000  
**Swagger API docs:** http://127.0.0.1:8000/api/docs

The SQLite database is created automatically in `data/nova.db`. On an empty database the app seeds **36 fictional demo students** using `example.org` addresses. Seeding is idempotent and never overwrites existing records. To start with an empty roster, set `NOVA_DEMO_SEED=false` before running. You can override the database path with `NOVA_DB_PATH`.

## Architecture

```
frontend/
  index.html              Responsive single-page dashboard
  styles.css              Custom design system and breakpoints
  app.js                  Accessible interactions and REST client
backend/
  app/
    main.py               FastAPI routes, analytics, export
    schemas.py            Pydantic validation
    database.py           SQLite connection and schema
    seed.py               Deterministic, fictional demonstration data
  tests/test_api.py       Isolated API integration tests
  requirements.txt
.github/workflows/ci.yml Automated backend tests and JS syntax verification
```

**Technology:** Python · FastAPI · Pydantic · SQLite · HTML5 · CSS3 · Vanilla JavaScript · Pytest · GitHub Actions.

The backend serves the frontend under the same origin, so **there are no localhost CORS workarounds**. The built-in Swagger/OpenAPI page shows every request, schema and response.

## API overview

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Operational health check |
| GET | `/api/dashboard` | Statistics, departments, enrollment trend, watchlist and activity |
| GET | `/api/students` | Search, filter, sort, paginate records |
| GET | `/api/students/{id}` | Read a student's details |
| POST | `/api/students` | Create a student |
| PATCH | `/api/students/{id}` | Update fields |
| DELETE | `/api/students/{id}` | Delete a student |
| GET | `/api/students/export` | Export currently filtered roster to CSV |
| GET | `/api/activity` | Read recent changes |
| GET | `/api/docs` | Interactive REST API documentation |

Validation and data integrity include: unique case-insensitive student IDs/emails, length and format checks, GPA 0–4, attendance 0–100, academic year 1–6, valid statuses, parameterized SQL, transactional writes, SQL constraints, and formula-safe CSV export.

## Run automated tests

```bash
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests -q
node --check frontend/app.js
```

Tests cover create/read/update/delete, input validation, duplicate rejection, filtering, pagination, CSV, wellness rules, activity logging, and missing records. The test suite uses a **temporary isolated database** and never mutates your real roster.

## Reviewer demo (90 seconds)

1. Open the dashboard, briefly show the live metrics and enrollment trends.
2. Navigate to **Students**: search for someone, filter by program/status, and open their detailed profile.
3. Click **Add student**, add a fictional entry, and show it in the directory.
4. Edit the GPA or attendance to see the watchlist update. Show the confirmation before deleting the fictional entry.
5. Export a CSV and open **Activity log**; finish on the API documentation and green CI checks.

## Scope / responsible use

This is an **internship demonstration**, not a production student information system. It deliberately uses fictional records and does not implement authentication or role-based authorization. **Do not deploy publicly with real student data.** Before real-world use: add verified admin login, granular roles, CSRF/session protections if using cookies, rate limiting, audit attribution, backup/restore, migration tooling, retention rules, and secure infrastructure.

### Original work
Designed and developed for an internship application by [@22koki](https://github.com/22koki). License not provided; all rights reserved.
