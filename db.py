import os
import sqlite3
import secrets
from contextlib import contextmanager
from typing import Optional


def _get_db_path() -> str:
    return os.environ.get("DATABASE_URL", "data/mentoring.db")


@contextmanager
def _conn():
    path = _get_db_path()
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


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS mentors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                dashboard_token TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mentor_id INTEGER REFERENCES mentors(id),
                email TEXT
            );
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ai_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_id INTEGER REFERENCES assessments(id),
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS mentor_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_id INTEGER REFERENCES assessments(id),
                feedback_text TEXT NOT NULL,
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
    # Migrations for existing databases
    for migration in [
        "ALTER TABLE students ADD COLUMN email TEXT",
        "ALTER TABLE assessments ADD COLUMN drive_folder_id TEXT",
    ]:
        try:
            with _conn() as con:
                con.execute(migration)
        except Exception:
            pass


# --- Mentors ---

def get_mentors() -> list:
    with _conn() as con:
        return [dict(r) for r in con.execute("SELECT * FROM mentors ORDER BY name").fetchall()]


def get_mentor_by_id(mentor_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM mentors WHERE id = ?", (mentor_id,)).fetchone()
        return dict(row) if row else None


def add_mentor(name: str, email: str) -> dict:
    token = secrets.token_urlsafe(16)
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO mentors (name, email, dashboard_token) VALUES (?, ?, ?)",
            (name, email, token),
        )
        return {"id": cur.lastrowid, "name": name, "email": email, "dashboard_token": token}


def update_mentor(mentor_id: int, name: str, email: str) -> None:
    with _conn() as con:
        con.execute("UPDATE mentors SET name = ?, email = ? WHERE id = ?", (name, email, mentor_id))


# --- Students ---

def get_students() -> list:
    with _conn() as con:
        return [dict(r) for r in con.execute(
            "SELECT s.*, m.name as mentor_name FROM students s "
            "LEFT JOIN mentors m ON s.mentor_id = m.id ORDER BY s.name"
        ).fetchall()]


def get_student_by_id(student_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None


def add_student(name: str, mentor_id: int, email: str = "") -> dict:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO students (name, mentor_id, email) VALUES (?, ?, ?)",
            (name, mentor_id, email),
        )
        return {"id": cur.lastrowid, "name": name, "mentor_id": mentor_id, "email": email}


def update_student(student_id: int, name: str, mentor_id: int, email: str = "") -> None:
    with _conn() as con:
        con.execute(
            "UPDATE students SET name = ?, mentor_id = ?, email = ? WHERE id = ?",
            (name, mentor_id, email, student_id),
        )


# --- Assessments ---

def create_assessment(
    student_id: int, round_num: int, competency_ratings: str, reflections: str
) -> dict:
    student_token = secrets.token_urlsafe(16)
    mentor_token = secrets.token_urlsafe(16)
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO assessments
               (student_id, round, competency_ratings, reflections, student_token, mentor_token, status)
               VALUES (?, ?, ?, ?, ?, ?, 'submitted')""",
            (student_id, round_num, competency_ratings, reflections, student_token, mentor_token),
        )
        row = con.execute("SELECT * FROM assessments WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def get_assessment_by_id(assessment_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM assessments WHERE id = ?", (assessment_id,)).fetchone()
        return dict(row) if row else None


def update_assessment(assessment_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with _conn() as con:
        con.execute(
            f"UPDATE assessments SET {cols} WHERE id = ?",
            (*fields.values(), assessment_id),
        )


def get_assessments_by_mentor(mentor_id: int) -> list:
    with _conn() as con:
        return [dict(r) for r in con.execute(
            """SELECT a.*, s.name as student_name
               FROM assessments a
               JOIN students s ON a.student_id = s.id
               WHERE s.mentor_id = ?
               ORDER BY a.submitted_at DESC""",
            (mentor_id,),
        ).fetchall()]


def get_all_assessments() -> list:
    with _conn() as con:
        return [dict(r) for r in con.execute(
            """SELECT a.*, s.name as student_name, m.name as mentor_name
               FROM assessments a
               JOIN students s ON a.student_id = s.id
               JOIN mentors m ON s.mentor_id = m.id
               ORDER BY a.submitted_at DESC"""
        ).fetchall()]


# --- AI Reviews ---

def save_ai_review(assessment_id: int, content: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO ai_reviews (assessment_id, content) VALUES (?, ?)",
            (assessment_id, content),
        )


def get_ai_review(assessment_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM ai_reviews WHERE assessment_id = ? ORDER BY created_at DESC LIMIT 1",
            (assessment_id,),
        ).fetchone()
        return dict(row) if row else None


# --- Mentor Feedback ---

def save_mentor_feedback(assessment_id: int, feedback_text: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM mentor_feedback WHERE assessment_id = ?", (assessment_id,))
        con.execute(
            "INSERT INTO mentor_feedback (assessment_id, feedback_text) VALUES (?, ?)",
            (assessment_id, feedback_text),
        )


def get_mentor_feedback(assessment_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM mentor_feedback WHERE assessment_id = ?", (assessment_id,)
        ).fetchone()
        return dict(row) if row else None
