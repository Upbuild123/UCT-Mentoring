import os
import secrets
from contextlib import contextmanager
from typing import Optional

def _get_database_url() -> str:
    # Allow assembling from parts if full URL has TOML escaping issues
    host = os.environ.get("DB_HOST")
    if host:
        user = os.environ.get("DB_USER", "")
        password = os.environ.get("DB_PASSWORD", "")
        name = os.environ.get("DB_NAME", "neondb")
        return f"postgresql://{user}:{password}@{host}/{name}?sslmode=require"
    return os.environ.get("DATABASE_URL", "data/mentoring.db")

DATABASE_URL = _get_database_url()
_IS_POSTGRES = DATABASE_URL.startswith(("postgresql://", "postgres://"))
_PH = "%s" if _IS_POSTGRES else "?"  # query placeholder


@contextmanager
def _conn():
    if _IS_POSTGRES:
        import psycopg2
        import psycopg2.extras
        con = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield con
            con.commit()
        finally:
            con.close()
    else:
        import sqlite3
        path = DATABASE_URL
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        finally:
            con.close()


def _fetchall(con, sql: str, params=()) -> list:
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def _fetchone(con, sql: str, params=()) -> Optional[dict]:
    cur = con.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def _execute(con, sql: str, params=()):
    cur = con.cursor()
    cur.execute(sql, params)
    return cur


def init_db() -> None:
    serial = "SERIAL" if _IS_POSTGRES else "INTEGER"
    autoincrement = "" if _IS_POSTGRES else "AUTOINCREMENT"

    statements = [
        f"""CREATE TABLE IF NOT EXISTS mentors (
            id {serial} PRIMARY KEY {autoincrement},
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            dashboard_token TEXT NOT NULL UNIQUE
        )""",
        f"""CREATE TABLE IF NOT EXISTS students (
            id {serial} PRIMARY KEY {autoincrement},
            name TEXT NOT NULL,
            mentor_id INTEGER REFERENCES mentors(id),
            email TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS assessments (
            id {serial} PRIMARY KEY {autoincrement},
            student_id INTEGER REFERENCES students(id),
            round INTEGER NOT NULL,
            video_drive_url TEXT,
            transcript TEXT,
            competency_ratings TEXT,
            reflections TEXT,
            status TEXT NOT NULL DEFAULT 'submitted',
            student_token TEXT UNIQUE,
            mentor_token TEXT UNIQUE,
            drive_folder_url TEXT,
            drive_folder_id TEXT,
            pdf_drive_url TEXT,
            error_message TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS ai_reviews (
            id {serial} PRIMARY KEY {autoincrement},
            assessment_id INTEGER REFERENCES assessments(id),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS mentor_feedback (
            id {serial} PRIMARY KEY {autoincrement},
            assessment_id INTEGER REFERENCES assessments(id),
            feedback_text TEXT NOT NULL,
            mentor_ratings TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]

    with _conn() as con:
        for stmt in statements:
            _execute(con, stmt)

    # Migrations for existing databases
    migrations = [
        "ALTER TABLE students ADD COLUMN email TEXT",
        "ALTER TABLE assessments ADD COLUMN drive_folder_id TEXT",
        "ALTER TABLE mentor_feedback ADD COLUMN mentor_ratings TEXT",
    ]
    for migration in migrations:
        try:
            with _conn() as con:
                _execute(con, migration)
        except Exception:
            pass


# --- Mentors ---

def get_mentors() -> list:
    with _conn() as con:
        return _fetchall(con, "SELECT * FROM mentors ORDER BY name")


def get_mentor_by_id(mentor_id: int) -> Optional[dict]:
    with _conn() as con:
        return _fetchone(con, f"SELECT * FROM mentors WHERE id = {_PH}", (mentor_id,))


def add_mentor(name: str, email: str) -> dict:
    token = secrets.token_urlsafe(16)
    with _conn() as con:
        if _IS_POSTGRES:
            row = _fetchone(con,
                f"INSERT INTO mentors (name, email, dashboard_token) VALUES ({_PH}, {_PH}, {_PH}) RETURNING id",
                (name, email, token),
            )
            new_id = row["id"]
        else:
            cur = _execute(con,
                f"INSERT INTO mentors (name, email, dashboard_token) VALUES ({_PH}, {_PH}, {_PH})",
                (name, email, token),
            )
            new_id = cur.lastrowid
        return {"id": new_id, "name": name, "email": email, "dashboard_token": token}


def update_mentor(mentor_id: int, name: str, email: str) -> None:
    with _conn() as con:
        _execute(con, f"UPDATE mentors SET name = {_PH}, email = {_PH} WHERE id = {_PH}", (name, email, mentor_id))


# --- Students ---

def get_students() -> list:
    with _conn() as con:
        return _fetchall(con,
            "SELECT s.*, m.name as mentor_name FROM students s "
            "LEFT JOIN mentors m ON s.mentor_id = m.id ORDER BY s.name"
        )


def get_student_by_id(student_id: int) -> Optional[dict]:
    with _conn() as con:
        return _fetchone(con, f"SELECT * FROM students WHERE id = {_PH}", (student_id,))


def add_student(name: str, mentor_id: int, email: str = "") -> dict:
    with _conn() as con:
        if _IS_POSTGRES:
            row = _fetchone(con,
                f"INSERT INTO students (name, mentor_id, email) VALUES ({_PH}, {_PH}, {_PH}) RETURNING id",
                (name, mentor_id, email),
            )
            new_id = row["id"]
        else:
            cur = _execute(con,
                f"INSERT INTO students (name, mentor_id, email) VALUES ({_PH}, {_PH}, {_PH})",
                (name, mentor_id, email),
            )
            new_id = cur.lastrowid
        return {"id": new_id, "name": name, "mentor_id": mentor_id, "email": email}


def update_student(student_id: int, name: str, mentor_id: int, email: str = "") -> None:
    with _conn() as con:
        _execute(con,
            f"UPDATE students SET name = {_PH}, mentor_id = {_PH}, email = {_PH} WHERE id = {_PH}",
            (name, mentor_id, email, student_id),
        )


# --- Assessments ---

def create_assessment(
    student_id: int, round_num: int, competency_ratings: str, reflections: str
) -> dict:
    student_token = secrets.token_urlsafe(16)
    mentor_token = secrets.token_urlsafe(16)
    with _conn() as con:
        if _IS_POSTGRES:
            row = _fetchone(con,
                f"""INSERT INTO assessments
                   (student_id, round, competency_ratings, reflections, student_token, mentor_token, status)
                   VALUES ({_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, 'submitted') RETURNING id""",
                (student_id, round_num, competency_ratings, reflections, student_token, mentor_token),
            )
            new_id = row["id"]
        else:
            cur = _execute(con,
                f"""INSERT INTO assessments
                   (student_id, round, competency_ratings, reflections, student_token, mentor_token, status)
                   VALUES ({_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH}, 'submitted')""",
                (student_id, round_num, competency_ratings, reflections, student_token, mentor_token),
            )
            new_id = cur.lastrowid
        return _fetchone(con, f"SELECT * FROM assessments WHERE id = {_PH}", (new_id,))


def get_assessment_by_id(assessment_id: int) -> Optional[dict]:
    with _conn() as con:
        return _fetchone(con, f"SELECT * FROM assessments WHERE id = {_PH}", (assessment_id,))


def update_assessment(assessment_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = {_PH}" for k in fields)
    with _conn() as con:
        _execute(con,
            f"UPDATE assessments SET {cols} WHERE id = {_PH}",
            (*fields.values(), assessment_id),
        )


def get_assessments_by_student(student_id: int) -> list:
    with _conn() as con:
        return _fetchall(con,
            f"SELECT * FROM assessments WHERE student_id = {_PH} ORDER BY round",
            (student_id,),
        )


def get_assessments_by_mentor(mentor_id: int) -> list:
    with _conn() as con:
        return _fetchall(con,
            f"""SELECT a.*, s.name as student_name
               FROM assessments a
               JOIN students s ON a.student_id = s.id
               WHERE s.mentor_id = {_PH}
               ORDER BY a.submitted_at DESC""",
            (mentor_id,),
        )


def get_all_assessments() -> list:
    with _conn() as con:
        return _fetchall(con,
            """SELECT a.*, s.name as student_name, m.name as mentor_name
               FROM assessments a
               JOIN students s ON a.student_id = s.id
               JOIN mentors m ON s.mentor_id = m.id
               ORDER BY a.submitted_at DESC"""
        )


# --- AI Reviews ---

def save_ai_review(assessment_id: int, content: str) -> None:
    with _conn() as con:
        _execute(con,
            f"INSERT INTO ai_reviews (assessment_id, content) VALUES ({_PH}, {_PH})",
            (assessment_id, content),
        )


def get_ai_review(assessment_id: int) -> Optional[dict]:
    with _conn() as con:
        return _fetchone(con,
            f"SELECT * FROM ai_reviews WHERE assessment_id = {_PH} ORDER BY created_at DESC LIMIT 1",
            (assessment_id,),
        )


# --- Mentor Feedback ---

def save_mentor_feedback(assessment_id: int, feedback_text: str, mentor_ratings: str = "{}") -> None:
    with _conn() as con:
        _execute(con, f"DELETE FROM mentor_feedback WHERE assessment_id = {_PH}", (assessment_id,))
        _execute(con,
            f"INSERT INTO mentor_feedback (assessment_id, feedback_text, mentor_ratings) VALUES ({_PH}, {_PH}, {_PH})",
            (assessment_id, feedback_text, mentor_ratings),
        )


def get_mentor_feedback(assessment_id: int) -> Optional[dict]:
    with _conn() as con:
        return _fetchone(con,
            f"SELECT * FROM mentor_feedback WHERE assessment_id = {_PH}",
            (assessment_id,),
        )
