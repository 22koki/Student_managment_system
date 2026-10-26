"""Explicit, deterministic synthetic demo records (never real student data)."""
from datetime import date, timedelta, datetime, timezone
from .database import connect, database_path, initialize

NAMES = [
    ("Amara", "Okafor"), ("Ethan", "Brooks"), ("Amina", "Hassan"),
    ("Leo", "Mendez"), ("Zuri", "Kamau"), ("Sofia", "Reyes"),
    ("Noah", "Patel"), ("Isla", "Morgan"), ("Kofi", "Mensah"),
    ("Maya", "Chen"), ("Ari", "Johnson"), ("Nia", "Wanjiku"),
    ("Elijah", "Kimani"), ("Ivy", "Thompson"), ("Omar", "Farouk"),
    ("Chloe", "Nguyen"), ("Tariq", "Ahmed"), ("Lena", "Fischer"),
    ("Jayden", "Mwangi"), ("Fatima", "Ali"), ("Kai", "Anderson"),
    ("Leila", "Otieno"), ("Lucas", "Silva"), ("Imani", "Carter"),
    ("Rayan", "Khan"), ("Aria", "Bennett"), ("Ezra", "Njoroge"),
    ("Zara", "Williams"), ("Dante", "Roberts"), ("Hana", "Yusuf"),
    ("Samira", "Abdi"), ("Finn", "Walker"), ("Priya", "Shah"),
    ("Malik", "Brown"), ("Mila", "Park"), ("Theo", "Evans")
]
PROGRAMS = [
    "Computer Science", "Business Administration", "Psychology",
    "Design & Media", "Engineering", "Data Science",
    "Environmental Studies"
]

def seed_demo(path=None):
    target = path if path is not None else database_path()
    initialize(target)
    with connect(target) as conn:
        if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]:
            return 0
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        today = date.today()
        for i, (first, last) in enumerate(NAMES):
            program = PROGRAMS[(i * 3 + i // 7) % len(PROGRAMS)]
            gpa = round(min(4, max(1.45, 2.35 + ((i * 17) % 150) / 100)), 2)
            attendance = max(51, min(100, 64 + (i * 11) % 38))
            status = "Graduated" if i in (9, 25) else "On leave" if i in (18, 29) else "Active"
            enrolled = today - timedelta(days=(i * 9) + (i % 4) * 7)
            conn.execute(
                """INSERT INTO students
                   (student_number, first_name, last_name, email, phone, program, year,
                    gpa, attendance, status, enrolled_on, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"NC-{today.year}-{i+1:03d}", first, last,
                 f"{first.lower()}.{last.lower()}.{i+1}@example.org", None,
                 program, (i % 4) + 1, gpa, attendance, status,
                 enrolled.isoformat(), "", now, now)
            )
        conn.execute(
            """INSERT INTO activity (student_id, student_name, action, description, created_at)
               VALUES (NULL, 'Demo workspace', 'demo', ?, ?)""",
            ("Sample roster ready — explore, edit, or add your own records.", now)
        )
        return len(NAMES)

if __name__ == "__main__":
    count = seed_demo()
    print(f"Created {count} synthetic students. Database: {database_path()}")
