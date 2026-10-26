"""NOVA Campus — documented REST APIs and a dependency-free frontend."""
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
import csv
import os
import sqlite3

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .database import connect, initialize
from .schemas import StudentCreate, StudentPatch
from .seed import seed_demo

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
COLUMNS = ("student_number", "first_name", "last_name", "email", "phone",
           "program", "year", "gpa", "attendance", "status", "enrolled_on", "notes")
SORTS = {
    "newest": "created_at DESC, id DESC",
    "oldest": "created_at ASC, id ASC",
    "name": "last_name COLLATE NOCASE ASC, first_name COLLATE NOCASE ASC",
    "gpa": "gpa DESC, last_name ASC",
    "attendance": "attendance ASC, last_name ASC",
}
STATUS_VALUES = {"Active", "On leave", "Graduated", "Suspended"}

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def present(row):
    obj = dict(row)
    if "gpa" in obj and "attendance" in obj:
        risk = obj["status"] == "Active" and (obj["gpa"] < 2 or obj["attendance"] < 75)
        obj["health"] = ("At risk" if risk else
                         "Excellent" if obj["gpa"] >= 3.5 and obj["attendance"] >= 90 else
                         "On track")
        obj["risk_reason"] = (
            "Low GPA and attendance" if obj["gpa"] < 2 and obj["attendance"] < 75 else
            "GPA below 2.0" if obj["gpa"] < 2 else
            "Attendance below 75%" if obj["attendance"] < 75 else ""
        ) if risk else ""
    return obj

def where_sql(q="", status="", program="", year=None):
    clauses = []
    args = []
    if q:
        clauses.append("(student_number LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR program LIKE ?)")
        term = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        # With the ESCAPE clause, literal search terms cannot become SQL wildcards.
        clauses[-1] = clauses[-1].replace(" LIKE ?", " LIKE ? ESCAPE '\\'")
        args.extend([term] * 5)
    if status:
        clauses.append("status = ?")
        args.append(status)
    if program:
        clauses.append("program = ?")
        args.append(program)
    if year is not None:
        clauses.append("year = ?")
        args.append(year)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", args

def conflict_error(exc):
    message = str(exc).lower()
    if "student_number" in message:
        return HTTPException(409, "That student ID is already registered.")
    if "email" in message:
        return HTTPException(409, "That email address is already registered.")
    return HTTPException(409, "Student record conflicts with an existing record.")

def create_app(db_path=None, seed=None):
    if seed is None:
        seed = os.environ.get("NOVA_DEMO_SEED", "true").lower() in {"true", "1", "yes"}

    @asynccontextmanager
    async def lifespan(app):
        initialize(db_path)
        if seed:
            seed_demo(db_path)
        yield

    app = FastAPI(
        title="NOVA Campus API", version="1.0.0",
        description="Student roster, intelligent summaries, activity trail and CSV exports.",
        lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "nova-campus", "version": "1.0.0"}

    @app.get("/api/students")
    def list_students(
        q: str = Query("", max_length=120),
        status: str = Query("", max_length=30),
        program: str = Query("", max_length=80),
        year: int | None = Query(None, ge=1, le=6),
        sort: str = Query("newest"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
    ):
        if sort not in SORTS:
            raise HTTPException(422, "Unsupported sorting option.")
        if status and status not in STATUS_VALUES:
            raise HTTPException(422, "Unknown student status.")
        where, params = where_sql(q, status, program, year)
        with connect(db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM students" + where, params).fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM students" + where + " ORDER BY " + SORTS[sort] + " LIMIT ? OFFSET ?",
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()
            programs = [r[0] for r in conn.execute(
                "SELECT DISTINCT program FROM students ORDER BY program").fetchall()]
        return {"items": [present(r) for r in rows], "total": total,
                "page": page, "page_size": page_size,
                "pages": max(1, (total + page_size - 1) // page_size),
                "programs": programs}

    @app.get("/api/students/export")
    def export_students(
        q: str = Query("", max_length=120),
        status: str = Query("", max_length=30),
        program: str = Query("", max_length=80),
        year: int | None = Query(None, ge=1, le=6),
    ):
        if status and status not in STATUS_VALUES:
            raise HTTPException(422, "Unknown student status.")
        where, params = where_sql(q, status, program, year)
        with connect(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM students" + where + " ORDER BY last_name COLLATE NOCASE", params
            ).fetchall()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Student ID", "First name", "Last name", "Email", "Phone", "Program",
                         "Year", "GPA", "Attendance (%)", "Status", "Enrolled on", "Notes"])
        for row in rows:
            # Prevent spreadsheet formula injection when exports are opened in Excel/Sheets.
            def safe(value):
                value = "" if value is None else str(value)
                return "'" + value if value and value.lstrip().startswith(("=", "+", "-", "@")) else value
            writer.writerow([safe(row[col]) for col in COLUMNS])
        return Response(
            content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="nova-campus-students.csv"'},
        )

    @app.get("/api/students/{student_id}")
    def get_student(student_id: int):
        with connect(db_path) as conn:
            row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Student not found.")
        return present(row)

    @app.post("/api/students", status_code=201)
    def add_student(payload: StudentCreate):
        values = payload.model_dump(mode="json")
        now = utc_now()
        try:
            with connect(db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO students (" + ",".join(COLUMNS) + ",created_at,updated_at) "
                    "VALUES (" + ",".join("?" for _ in range(len(COLUMNS) + 2)) + ")",
                    [*(values[col] for col in COLUMNS), now, now],
                )
                student_id = cursor.lastrowid
                name = values["first_name"] + " " + values["last_name"]
                conn.execute(
                    "INSERT INTO activity (student_id, student_name, action, description, created_at) VALUES (?, ?, ?, ?, ?)",
                    (student_id, name, "created", "New student enrolled into " + values["program"], now),
                )
                row = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise conflict_error(exc)
        return present(row)

    @app.patch("/api/students/{student_id}")
    def update_student(student_id: int, payload: StudentPatch):
        changes = payload.model_dump(exclude_unset=True, mode="json")
        if not changes:
            raise HTTPException(422, "Provide at least one field to update.")
        for key, value in changes.items():
            if value is None and key != "phone":
                raise HTTPException(422, f"{key} cannot be null.")
        try:
            with connect(db_path) as conn:
                original = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
                if original is None:
                    raise HTTPException(404, "Student not found.")
                now = utc_now()
                updates = [f"{field}=?" for field in changes]
                conn.execute(
                    "UPDATE students SET " + ",".join(updates) + ",updated_at=? WHERE id=?",
                    [*changes.values(), now, student_id],
                )
                row = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
                conn.execute(
                    "INSERT INTO activity (student_id, student_name, action, description, created_at) VALUES (?, ?, ?, ?, ?)",
                    (student_id, row["first_name"] + " " + row["last_name"],
                     "updated", "Updated " + ", ".join(changes.keys()), now),
                )
        except sqlite3.IntegrityError as exc:
            raise conflict_error(exc)
        return present(row)

    @app.delete("/api/students/{student_id}", status_code=204)
    def delete_student(student_id: int):
        with connect(db_path) as conn:
            row = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "Student not found.")
            name = row["first_name"] + " " + row["last_name"]
            conn.execute("DELETE FROM students WHERE id=?", (student_id,))
            conn.execute(
                "INSERT INTO activity (student_id, student_name, action, description, created_at) VALUES (?, ?, ?, ?, ?)",
                (student_id, name, "deleted", "Student record permanently deleted.", utc_now()),
            )
        return Response(status_code=204)

    @app.get("/api/dashboard")
    def dashboard():
        with connect(db_path) as conn:
            students = [present(r) for r in conn.execute("SELECT * FROM students").fetchall()]
            activities = [dict(r) for r in conn.execute(
                "SELECT * FROM activity ORDER BY id DESC LIMIT 7").fetchall()]
        total = len(students)
        active = [s for s in students if s["status"] == "Active"]
        at_risk = [s for s in active if s["health"] == "At risk"]
        average_gpa = round(sum(s["gpa"] for s in students) / total, 2) if total else 0
        average_attendance = round(sum(s["attendance"] for s in students) / total) if total else 0
        programs = {}
        for s in students:
            programs[s["program"]] = programs.get(s["program"], 0) + 1
        departments = [{"name": key, "count": value} for key, value in
                       sorted(programs.items(), key=lambda item: -item[1])]
        today = date.today()
        months = []
        for offset in range(5, -1, -1):
            year = today.year
            month = today.month - offset
            while month <= 0:
                year -= 1
                month += 12
            key = f"{year:04d}-{month:02d}"
            months.append({"key": key, "label": date(year, month, 1).strftime("%b"),
                           "count": sum(s["enrolled_on"][:7] == key for s in students)})
        return {
            "total": total, "active": len(active), "at_risk": len(at_risk),
            "average_gpa": average_gpa, "average_attendance": average_attendance,
            "departments": departments, "enrollments": months,
            "recent_activity": activities,
            "risk_students": sorted(at_risk, key=lambda s: (s["attendance"], s["gpa"]))[:5],
            "status_breakdown": {
                name: sum(s["status"] == name for s in students)
                for name in ("Active", "On leave", "Graduated", "Suspended")
            },
        }

    @app.get("/api/activity")
    def activity(limit: int = Query(30, ge=1, le=100)):
        with connect(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {"items": [dict(r) for r in rows]}

    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(FRONTEND / "index.html"))

    return app

app = create_app()
