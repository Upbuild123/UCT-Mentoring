# Streamlit Mentoring Assessment App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pure Streamlit + SQLite mentoring assessment web app with Google Drive, OpenAI, and Resend integrations.

**Architecture:** Multi-page Streamlit app (`pages/` folder) with a shared `db.py` data layer and `services/` for external integrations. Student submissions trigger synchronous processing (Drive upload → audio extraction → transcription → AI review → PDF → email) with a progress bar. No background job queue.

**Tech Stack:** Python 3.11+, Streamlit 1.32+, SQLite (stdlib `sqlite3`), `openai`, `google-api-python-client`, `google-auth`, `resend`, `fpdf2`, `ffmpeg` (system binary via subprocess)

---

## File Map

| File | Responsibility |
|---|---|
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
| `config.py` | Constants: competency list, reflection questions |
| `db.py` | SQLite schema init + all CRUD queries |
| `seed.py` | Idempotent seed for initial mentors/students |
| `app.py` | Streamlit landing/redirect page |
| `services/__init__.py` | Empty package marker |
| `services/drive.py` | Google Drive: create folders, upload files, return shareable links |
| `services/openai_service.py` | ffmpeg audio extraction + Whisper transcription + AI review |
| `services/email.py` | Resend mentor notification email |
| `services/pdf.py` | fpdf2 PDF generation |
| `services/processor.py` | Pipeline orchestrator: calls all services in order |
| `pages/1_Student_Submission.py` | Student form: name, round, ratings, reflections, video upload |
| `pages/2_Mentor_Review.py` | Mentor review page (URL param: `?assessment_id=X`) |
| `pages/3_Mentor_Dashboard.py` | Mentor assessment list (URL param: `?mentor_id=X`) |
| `pages/4_Admin.py` | Admin: assessments table, manage mentors, manage students |
| `tests/test_db.py` | Unit tests for all db.py functions |
| `tests/test_services.py` | Unit tests for services (mocked external APIs) |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `uploads/.gitkeep`
- Create: `data/.gitkeep`
- Create: `services/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p uploads data services tests pages
touch services/__init__.py tests/__init__.py uploads/.gitkeep data/.gitkeep
```

- [ ] **Step 2: Create `requirements.txt`**

```
streamlit>=1.32.0
openai>=1.30.0
google-api-python-client>=2.120.0
google-auth>=2.29.0
resend>=2.0.0
fpdf2>=2.7.9
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Create `.env.example`**

```
DATABASE_URL=data/mentoring.db
PORT=8501
APP_URL=http://localhost:8501
OPENAI_API_KEY=
RESEND_API_KEY=
GOOGLE_DRIVE_PARENT_FOLDER_ID=
GOOGLE_CLIENT_EMAIL=
GOOGLE_PRIVATE_KEY=
EMAIL_FROM=Mentoring Program <noreply@example.com>
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages installed with no errors.

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt .env.example uploads/.gitkeep data/.gitkeep services/__init__.py tests/__init__.py
git commit -m "chore: project setup and dependencies"
```

---

## Task 2: Constants (`config.py`)

**Files:**
- Create: `config.py`

- [ ] **Step 1: Create `config.py`**

```python
COMPETENCIES = [
    "Communication",
    "Problem Solving",
    "Technical Skills",
    "Collaboration",
    "Initiative",
    "Adaptability",
]

REFLECTION_QUESTIONS = [
    "What went well this round?",
    "What was most challenging?",
    "What are your goals for next round?",
]
```

- [ ] **Step 2: Commit**

```bash
git add config.py
git commit -m "chore: add competency and reflection constants"
```

---

## Task 3: Database Layer (`db.py`)

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_db.py
import os
import pytest
import sys
sys.path.insert(0, ".")


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "test.db"))
    import db
    db.init_db()
    return db


def test_add_and_get_mentor(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    assert mentor["name"] == "Alice"
    assert mentor["email"] == "alice@example.com"
    assert len(mentor["dashboard_token"]) > 8
    fetched = db.get_mentor_by_id(mentor["id"])
    assert fetched["name"] == "Alice"


def test_add_and_get_student(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    assert student["name"] == "Bob"
    fetched = db.get_student_by_id(student["id"])
    assert fetched["mentor_id"] == mentor["id"]


def test_create_and_update_assessment(isolated_db):
    db = isolated_db
    import json
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    ratings = json.dumps({"Communication": 4})
    reflections = json.dumps({"What went well?": "Everything"})
    assessment = db.create_assessment(student["id"], 1, ratings, reflections)
    assert assessment["status"] == "submitted"
    assert assessment["student_token"] is not None
    assert assessment["mentor_token"] is not None
    db.update_assessment(assessment["id"], status="complete", transcript="Hello world")
    updated = db.get_assessment_by_id(assessment["id"])
    assert updated["status"] == "complete"
    assert updated["transcript"] == "Hello world"


def test_get_assessments_by_mentor(isolated_db):
    db = isolated_db
    import json
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    db.create_assessment(student["id"], 1, "{}", "{}")
    db.create_assessment(student["id"], 2, "{}", "{}")
    rows = db.get_assessments_by_mentor(mentor["id"])
    assert len(rows) == 2


def test_ai_review_and_mentor_feedback(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    assessment = db.create_assessment(student["id"], 1, "{}", "{}")
    db.save_ai_review(assessment["id"], "Great job!")
    review = db.get_ai_review(assessment["id"])
    assert review["content"] == "Great job!"
    db.save_mentor_feedback(assessment["id"], "Keep it up")
    feedback = db.get_mentor_feedback(assessment["id"])
    assert feedback["feedback_text"] == "Keep it up"


def test_get_all_assessments(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    db.create_assessment(student["id"], 1, "{}", "{}")
    rows = db.get_all_assessments()
    assert len(rows) == 1
    assert rows[0]["student_name"] == "Bob"
    assert rows[0]["mentor_name"] == "Alice"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: ImportError or ModuleNotFoundError — `db` module does not exist yet.

- [ ] **Step 3: Create `db.py`**

```python
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
                mentor_id INTEGER REFERENCES mentors(id)
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


# --- Mentors ---

def get_mentors() -> list[dict]:
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

def get_students() -> list[dict]:
    with _conn() as con:
        return [dict(r) for r in con.execute(
            "SELECT s.*, m.name as mentor_name FROM students s "
            "LEFT JOIN mentors m ON s.mentor_id = m.id ORDER BY s.name"
        ).fetchall()]


def get_student_by_id(student_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None


def add_student(name: str, mentor_id: int) -> dict:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO students (name, mentor_id) VALUES (?, ?)", (name, mentor_id)
        )
        return {"id": cur.lastrowid, "name": name, "mentor_id": mentor_id}


def update_student(student_id: int, name: str, mentor_id: int) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE students SET name = ?, mentor_id = ? WHERE id = ?",
            (name, mentor_id, student_id),
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


def get_assessments_by_mentor(mentor_id: int) -> list[dict]:
    with _conn() as con:
        return [dict(r) for r in con.execute(
            """SELECT a.*, s.name as student_name
               FROM assessments a
               JOIN students s ON a.student_id = s.id
               WHERE s.mentor_id = ?
               ORDER BY a.submitted_at DESC""",
            (mentor_id,),
        ).fetchall()]


def get_all_assessments() -> list[dict]:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: database layer with SQLite schema and CRUD queries"
```

---

## Task 4: Seed Script (`seed.py`)

**Files:**
- Create: `seed.py`

- [ ] **Step 1: Create `seed.py`**

```python
import sys
sys.path.insert(0, ".")
import db


def seed():
    db.init_db()

    mentors_data = [
        ("Michael", "michael@upbuild.com"),
        ("Vipin", "vipin@example.com"),
    ]

    existing_mentors = {m["name"]: m for m in db.get_mentors()}
    mentor_ids = {}

    for name, email in mentors_data:
        if name not in existing_mentors:
            m = db.add_mentor(name, email)
            mentor_ids[name] = m["id"]
            print(f"Created mentor: {name} (dashboard_token: {m['dashboard_token']})")
        else:
            mentor_ids[name] = existing_mentors[name]["id"]
            print(f"Mentor already exists: {name}")

    students_data = [
        ("Student 1", "Michael"),
        ("Student 2", "Vipin"),
    ]

    existing_students = {s["name"]: s for s in db.get_students()}

    for name, mentor_name in students_data:
        if name not in existing_students:
            s = db.add_student(name, mentor_ids[mentor_name])
            print(f"Created student: {name} (mentor: {mentor_name})")
        else:
            print(f"Student already exists: {name}")


if __name__ == "__main__":
    seed()
    print("Seeding complete.")
```

- [ ] **Step 2: Run seed to verify it works**

```bash
python seed.py
```

Expected output:
```
Created mentor: Michael (dashboard_token: <token>)
Created mentor: Vipin (dashboard_token: <token>)
Created student: Student 1 (mentor: Michael)
Created student: Student 2 (mentor: Vipin)
Seeding complete.
```

- [ ] **Step 3: Run seed again to verify idempotency**

```bash
python seed.py
```

Expected: lines say "already exists" for all, no errors.

- [ ] **Step 4: Commit**

```bash
git add seed.py
git commit -m "feat: idempotent seed script for mentors and students"
```

---

## Task 5: Google Drive Service (`services/drive.py`)

**Files:**
- Create: `services/drive.py`
- Create: `tests/test_services.py` (partial — drive section)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_services.py
import os
import sys
import pytest
sys.path.insert(0, ".")


class TestDriveService:
    def test_create_folder_calls_api(self, mocker):
        mocker.patch.dict(os.environ, {
            "GOOGLE_CLIENT_EMAIL": "svc@proj.iam.gserviceaccount.com",
            "GOOGLE_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\\nFAKE\\n-----END PRIVATE KEY-----",
            "GOOGLE_DRIVE_PARENT_FOLDER_ID": "parent123",
        })
        mock_build = mocker.patch("services.drive._get_service")
        mock_service = mocker.MagicMock()
        mock_build.return_value = mock_service
        mock_files = mock_service.files.return_value
        mock_files.create.return_value.execute.return_value = {"id": "folder456"}
        mock_files.get.return_value.execute.return_value = {
            "webViewLink": "https://drive.google.com/folder/folder456"
        }

        from services.drive import create_student_round_folder
        folder_id, folder_url = create_student_round_folder("Alice", 1)
        assert folder_id == "folder456"
        assert "drive.google.com" in folder_url

    def test_upload_file_returns_url(self, mocker, tmp_path):
        mocker.patch.dict(os.environ, {
            "GOOGLE_CLIENT_EMAIL": "svc@proj.iam.gserviceaccount.com",
            "GOOGLE_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\\nFAKE\\n-----END PRIVATE KEY-----",
        })
        mock_build = mocker.patch("services.drive._get_service")
        mock_service = mocker.MagicMock()
        mock_build.return_value = mock_service
        mock_files = mock_service.files.return_value
        mock_files.create.return_value.execute.return_value = {"id": "file789"}
        mock_files.update.return_value.execute.return_value = {}
        mock_files.get.return_value.execute.return_value = {
            "webViewLink": "https://drive.google.com/file/file789"
        }

        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")

        from services.drive import upload_file
        url = upload_file(str(test_file), "folder456", "recording.mp4")
        assert "drive.google.com" in url
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_services.py::TestDriveService -v
```

Expected: ImportError — `services.drive` does not exist yet.

- [ ] **Step 3: Create `services/drive.py`**

```python
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account


def _get_service():
    private_key = os.environ["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n")
    creds = service_account.Credentials.from_service_account_info(
        {
            "type": "service_account",
            "client_email": os.environ["GOOGLE_CLIENT_EMAIL"],
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def _create_folder(service, name: str, parent_id: str) -> str:
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def _make_public(service, file_id: str) -> str:
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()
    file = service.files().get(fileId=file_id, fields="webViewLink").execute()
    return file["webViewLink"]


def create_student_round_folder(student_name: str, round_num: int) -> tuple[str, str]:
    """Create nested folders: parent/<student_name>/Round <round_num>. Returns (folder_id, folder_url)."""
    service = _get_service()
    parent_id = os.environ["GOOGLE_DRIVE_PARENT_FOLDER_ID"]
    student_folder_id = _create_folder(service, student_name, parent_id)
    round_folder_id = _create_folder(service, f"Round {round_num}", student_folder_id)
    folder_url = _make_public(service, round_folder_id)
    return round_folder_id, folder_url


def upload_file(local_path: str, folder_id: str, filename: str) -> str:
    """Upload a file to Drive folder and return its shareable URL."""
    service = _get_service()
    meta = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(body=meta, media_body=media, fields="id").execute()
    file_id = file["id"]
    file_url = _make_public(service, file_id)
    return file_url
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_services.py::TestDriveService -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/drive.py tests/test_services.py
git commit -m "feat: Google Drive service for folder creation and file upload"
```

---

## Task 6: OpenAI Service (`services/openai_service.py`)

**Files:**
- Create: `services/openai_service.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add failing tests to `tests/test_services.py`**

Append to the file:

```python
class TestOpenAIService:
    def test_extract_audio_calls_ffmpeg(self, mocker, tmp_path):
        mock_run = mocker.patch("subprocess.run")
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")
        audio = tmp_path / "audio.wav"

        from services.openai_service import extract_audio
        extract_audio(str(video), str(audio))
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args
        assert str(video) in call_args
        assert str(audio) in call_args

    def test_transcribe_returns_text(self, mocker, tmp_path):
        mocker.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"})
        mock_client = mocker.patch("services.openai_service.openai.OpenAI")
        mock_instance = mock_client.return_value
        mock_instance.audio.transcriptions.create.return_value.text = "Hello world"

        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"fake audio")

        from services.openai_service import transcribe
        result = transcribe(str(audio))
        assert result == "Hello world"

    def test_transcribe_returns_placeholder_without_key(self, mocker, tmp_path):
        mocker.patch.dict(os.environ, {}, clear=True)
        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"fake audio")

        from services.openai_service import transcribe
        result = transcribe(str(audio))
        assert "[transcription unavailable" in result.lower() or result == "[No API key configured]"

    def test_generate_ai_review_returns_text(self, mocker):
        mocker.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"})
        mock_client = mocker.patch("services.openai_service.openai.OpenAI")
        mock_instance = mock_client.return_value
        mock_instance.chat.completions.create.return_value.choices[0].message.content = "Great work!"

        assessment = {"competency_ratings": '{"Communication": 4}', "reflections": '{"Q": "A"}', "round": 1}
        from services.openai_service import generate_ai_review
        result = generate_ai_review(assessment, "This is the transcript.")
        assert result == "Great work!"

    def test_generate_ai_review_placeholder_without_key(self, mocker):
        mocker.patch.dict(os.environ, {}, clear=True)
        assessment = {"competency_ratings": "{}", "reflections": "{}", "round": 1}
        from services.openai_service import generate_ai_review
        result = generate_ai_review(assessment, "transcript")
        assert "[ai review unavailable" in result.lower() or result == "[No API key configured]"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_services.py::TestOpenAIService -v
```

Expected: ImportError — `services.openai_service` does not exist.

- [ ] **Step 3: Create `services/openai_service.py`**

```python
import os
import subprocess
import openai


def extract_audio(video_path: str, audio_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path,
        ],
        check=True,
        capture_output=True,
    )


def transcribe(audio_path: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "[No API key configured]"
    client = openai.OpenAI(api_key=api_key)
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(model="whisper-1", file=f)
    return result.text


def generate_ai_review(assessment: dict, transcript: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "[No API key configured]"
    import json
    ratings = json.loads(assessment.get("competency_ratings") or "{}")
    reflections = json.loads(assessment.get("reflections") or "{}")
    ratings_text = "\n".join(f"- {k}: {v}/5" for k, v in ratings.items())
    reflections_text = "\n".join(f"- {k}: {v}" for k, v in reflections.items())
    prompt = f"""You are a mentoring program coach reviewing a student's self-assessment for round {assessment['round']}.

Competency ratings (1-5):
{ratings_text}

Student reflections:
{reflections_text}

Session transcript:
{transcript}

Provide a constructive, encouraging review (3-5 paragraphs) highlighting strengths, areas for growth, and specific recommendations."""

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_services.py::TestOpenAIService -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/openai_service.py tests/test_services.py
git commit -m "feat: OpenAI service for audio transcription and AI review generation"
```

---

## Task 7: Email Service (`services/email.py`)

**Files:**
- Create: `services/email.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add failing tests to `tests/test_services.py`**

Append:

```python
class TestEmailService:
    def test_send_notification_calls_resend(self, mocker):
        mocker.patch.dict(os.environ, {
            "RESEND_API_KEY": "re_fake_key",
            "EMAIL_FROM": "test@example.com",
        })
        mock_resend = mocker.patch("services.email.resend.Emails.send")

        from services.email import send_mentor_notification
        send_mentor_notification(
            mentor_email="mentor@example.com",
            mentor_name="Alice",
            student_name="Bob",
            round_num=1,
            video_drive_url="https://drive.google.com/video",
            drive_folder_url="https://drive.google.com/folder",
            mentor_review_url="http://localhost:8501/Mentor_Review?assessment_id=1",
        )
        mock_resend.assert_called_once()
        call_kwargs = mock_resend.call_args[0][0]
        assert call_kwargs["to"] == "mentor@example.com"
        assert "Bob" in call_kwargs["html"]

    def test_send_notification_logs_without_key(self, mocker, capsys):
        mocker.patch.dict(os.environ, {}, clear=True)

        from services.email import send_mentor_notification
        send_mentor_notification(
            mentor_email="mentor@example.com",
            mentor_name="Alice",
            student_name="Bob",
            round_num=1,
            video_drive_url="https://drive.google.com/video",
            drive_folder_url="https://drive.google.com/folder",
            mentor_review_url="http://localhost:8501/Mentor_Review?assessment_id=1",
        )
        captured = capsys.readouterr()
        assert "mentor@example.com" in captured.out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_services.py::TestEmailService -v
```

Expected: ImportError — `services.email` does not exist.

- [ ] **Step 3: Create `services/email.py`**

```python
import os
import resend as resend_lib


def send_mentor_notification(
    mentor_email: str,
    mentor_name: str,
    student_name: str,
    round_num: int,
    video_drive_url: str,
    drive_folder_url: str,
    mentor_review_url: str,
) -> None:
    api_key = os.environ.get("RESEND_API_KEY", "")
    email_from = os.environ.get("EMAIL_FROM", "Mentoring Program <noreply@example.com>")

    subject = f"New assessment from {student_name} — Round {round_num}"
    html = f"""
<h2>New Mentoring Assessment</h2>
<p>Hi {mentor_name},</p>
<p><strong>{student_name}</strong> has submitted their Round {round_num} assessment.</p>
<ul>
  <li><a href="{drive_folder_url}">Drive folder (video, transcript, PDF)</a></li>
  <li><a href="{video_drive_url}">Video recording</a></li>
  <li><a href="{mentor_review_url}">Review and submit feedback</a></li>
</ul>
<p>Thank you for your time.</p>
"""

    if not api_key:
        print(f"[email] Would send to {mentor_email}: {subject}")
        print(f"[email] Mentor review URL: {mentor_review_url}")
        return

    resend_lib.api_key = api_key
    resend_lib.Emails.send({
        "from": email_from,
        "to": mentor_email,
        "subject": subject,
        "html": html,
    })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_services.py::TestEmailService -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/email.py tests/test_services.py
git commit -m "feat: Resend email service for mentor notifications"
```

---

## Task 8: PDF Service (`services/pdf.py`)

**Files:**
- Create: `services/pdf.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_services.py`:

```python
class TestPDFService:
    def test_generate_pdf_creates_file(self, tmp_path):
        import json
        assessment = {
            "round": 1,
            "submitted_at": "2026-06-02",
            "competency_ratings": json.dumps({"Communication": 4, "Initiative": 3}),
            "reflections": json.dumps({"What went well?": "Everything", "Goals?": "More practice"}),
        }
        student_name = "Bob"
        transcript = "This is the session transcript."
        ai_review = "Great progress shown this round."
        output_path = str(tmp_path / "assessment.pdf")

        from services.pdf import generate_pdf
        generate_pdf(assessment, student_name, transcript, ai_review, output_path)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 1000
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_services.py::TestPDFService -v
```

Expected: ImportError — `services.pdf` does not exist.

- [ ] **Step 3: Create `services/pdf.py`**

```python
import json
from fpdf import FPDF


def generate_pdf(
    assessment: dict,
    student_name: str,
    transcript: str,
    ai_review: str,
    output_path: str,
) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def heading(text: str, size: int = 14) -> None:
        pdf.set_font("Helvetica", style="B", size=size)
        pdf.cell(0, 10, text, ln=True)
        pdf.ln(2)

    def body(text: str, size: int = 11) -> None:
        pdf.set_font("Helvetica", size=size)
        pdf.multi_cell(0, 7, text)
        pdf.ln(3)

    heading(f"Mentoring Assessment — Round {assessment['round']}", size=16)
    body(f"Student: {student_name}")
    body(f"Submitted: {assessment.get('submitted_at', 'N/A')}")
    pdf.ln(4)

    heading("Competency Ratings")
    ratings = json.loads(assessment.get("competency_ratings") or "{}")
    for comp, score in ratings.items():
        body(f"{comp}: {score}/5")
    pdf.ln(4)

    heading("Reflections")
    reflections = json.loads(assessment.get("reflections") or "{}")
    for question, answer in reflections.items():
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.multi_cell(0, 7, question)
        body(answer or "(no answer)")
    pdf.ln(4)

    heading("Session Transcript")
    body(transcript or "(no transcript)")
    pdf.ln(4)

    heading("AI Review")
    body(ai_review or "(no review)")

    pdf.output(output_path)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_services.py::TestPDFService -v
```

Expected: 1 test PASS.

- [ ] **Step 5: Commit**

```bash
git add services/pdf.py tests/test_services.py
git commit -m "feat: fpdf2 PDF generation service"
```

---

## Task 9: Pipeline Orchestrator (`services/processor.py`)

**Files:**
- Create: `services/processor.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_services.py`:

```python
class TestProcessor:
    @pytest.fixture()
    def db_with_data(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", str(tmp_path / "test.db"))
        monkeypatch.setenv("APP_URL", "http://localhost:8501")
        import db
        db.init_db()
        mentor = db.add_mentor("Alice", "alice@example.com")
        student = db.add_student("Bob", mentor["id"])
        assessment = db.create_assessment(student["id"], 1, '{"Communication": 4}', '{"Q": "A"}')
        return db, assessment, student, mentor

    def test_process_assessment_success(self, mocker, tmp_path, db_with_data):
        db, assessment, student, mentor = db_with_data
        video_path = str(tmp_path / "video.mp4")
        open(video_path, "wb").write(b"fake video")

        mocker.patch("services.processor.drive.create_student_round_folder",
                     return_value=("folder123", "https://drive.google.com/folder"))
        mocker.patch("services.processor.drive.upload_file",
                     return_value="https://drive.google.com/file")
        mocker.patch("services.processor.openai_service.extract_audio")
        mocker.patch("services.processor.openai_service.transcribe", return_value="Transcript text")
        mocker.patch("services.processor.openai_service.generate_ai_review", return_value="AI review")
        mocker.patch("services.processor.pdf.generate_pdf")
        mocker.patch("services.processor.email.send_mentor_notification")

        from services.processor import process_assessment
        process_assessment(assessment["id"], video_path)

        updated = db.get_assessment_by_id(assessment["id"])
        assert updated["status"] == "complete"
        assert updated["transcript"] == "Transcript text"
        assert updated["drive_folder_url"] == "https://drive.google.com/folder"
        ai_review = db.get_ai_review(assessment["id"])
        assert ai_review["content"] == "AI review"

    def test_process_assessment_sets_error_on_failure(self, mocker, tmp_path, db_with_data):
        db, assessment, student, mentor = db_with_data
        video_path = str(tmp_path / "video.mp4")
        open(video_path, "wb").write(b"fake video")

        mocker.patch("services.processor.drive.create_student_round_folder",
                     side_effect=Exception("Drive failed"))

        from services.processor import process_assessment
        with pytest.raises(Exception, match="Drive failed"):
            process_assessment(assessment["id"], video_path)

        updated = db.get_assessment_by_id(assessment["id"])
        assert updated["status"] == "error"
        assert "Drive failed" in updated["error_message"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_services.py::TestProcessor -v
```

Expected: ImportError — `services.processor` does not exist.

- [ ] **Step 3: Create `services/processor.py`**

```python
import os
from typing import Callable, Optional
import db
from services import drive, openai_service, email, pdf


def process_assessment(
    assessment_id: int,
    video_path: str,
    progress_fn: Optional[Callable[[float, str], None]] = None,
) -> None:
    """
    Run the full processing pipeline for an assessment.
    progress_fn(fraction, message) is called at each step if provided.
    Raises on failure after setting assessment status to 'error'.
    """
    def _progress(fraction: float, message: str) -> None:
        if progress_fn:
            progress_fn(fraction, message)

    db.update_assessment(assessment_id, status="processing")
    try:
        assessment = db.get_assessment_by_id(assessment_id)
        student_row = db.get_student_by_id(assessment["student_id"])
        mentor_row = db.get_mentor_by_id(student_row["mentor_id"])

        _progress(0.0, "Uploading video to Google Drive...")
        folder_id, folder_url = drive.create_student_round_folder(
            student_row["name"], assessment["round"]
        )
        video_drive_url = drive.upload_file(video_path, folder_id, "recording.mp4")
        db.update_assessment(
            assessment_id,
            drive_folder_url=folder_url,
            video_drive_url=video_drive_url,
        )

        _progress(0.25, "Extracting audio...")
        audio_path = video_path.rsplit(".", 1)[0] + ".wav"
        openai_service.extract_audio(video_path, audio_path)

        _progress(0.40, "Transcribing audio...")
        transcript = openai_service.transcribe(audio_path)

        # Clean up temp files
        for path in (audio_path, video_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

        db.update_assessment(assessment_id, transcript=transcript)

        _progress(0.60, "Generating AI review...")
        ai_review_content = openai_service.generate_ai_review(assessment, transcript)
        db.save_ai_review(assessment_id, ai_review_content)

        _progress(0.75, "Generating PDF...")
        pdf_path = f"uploads/assessment_{assessment_id}.pdf"
        os.makedirs("uploads", exist_ok=True)
        pdf.generate_pdf(assessment, student_row["name"], transcript, ai_review_content, pdf_path)
        pdf_drive_url = drive.upload_file(pdf_path, folder_id, "assessment.pdf")
        try:
            os.remove(pdf_path)
        except FileNotFoundError:
            pass
        db.update_assessment(assessment_id, pdf_drive_url=pdf_drive_url)

        _progress(0.90, "Sending mentor notification...")
        app_url = os.environ.get("APP_URL", "http://localhost:8501")
        mentor_review_url = f"{app_url}/Mentor_Review?assessment_id={assessment_id}"
        email.send_mentor_notification(
            mentor_email=mentor_row["email"],
            mentor_name=mentor_row["name"],
            student_name=student_row["name"],
            round_num=assessment["round"],
            video_drive_url=video_drive_url,
            drive_folder_url=folder_url,
            mentor_review_url=mentor_review_url,
        )

        db.update_assessment(assessment_id, status="complete", error_message=None)
        _progress(1.0, "Complete!")

    except Exception as exc:
        db.update_assessment(assessment_id, status="error", error_message=str(exc))
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_services.py::TestProcessor -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add services/processor.py tests/test_services.py
git commit -m "feat: pipeline orchestrator with progress callback and error handling"
```

---

## Task 10: Landing Page (`app.py`)

**Files:**
- Create: `app.py`

- [ ] **Step 1: Create `app.py`**

```python
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import db
db.init_db()

import streamlit as st

st.set_page_config(page_title="Mentoring Assessment", layout="centered")
st.title("Mentoring Assessment Program")
st.markdown("""
Welcome. Use the sidebar to navigate:

- **Student Submission** — submit your video and self-assessment
- **Mentor Review** — review a student submission (use the link from your email)
- **Mentor Dashboard** — view all your assigned assessments
- **Admin** — manage mentors, students, and all assessments
""")
```

- [ ] **Step 2: Run the app to verify it starts**

```bash
streamlit run app.py
```

Expected: Streamlit app opens in browser at `http://localhost:8501` with the landing page text and sidebar showing the 4 pages.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Streamlit app entry point with db init"
```

---

## Task 11: Student Submission Page (`pages/1_Student_Submission.py`)

**Files:**
- Create: `pages/1_Student_Submission.py`

- [ ] **Step 1: Create `pages/1_Student_Submission.py`**

```python
import sys
sys.path.insert(0, ".")
import json
import os
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS
from services import processor

st.set_page_config(page_title="Student Submission", layout="centered")
st.title("Submit Your Assessment")

students = db.get_students()
if not students:
    st.warning("No students found. Ask your admin to add students.")
    st.stop()

student_map = {s["name"]: s["id"] for s in students}
selected_name = st.selectbox("Your name", list(student_map.keys()))
student_id = student_map[selected_name]

round_num = st.number_input("Round number", min_value=1, max_value=50, value=1, step=1)

st.subheader("Competency Self-Ratings")
st.caption("Rate yourself from 1 (needs work) to 5 (excellent)")
ratings = {}
for comp in COMPETENCIES:
    ratings[comp] = st.slider(comp, min_value=1, max_value=5, value=3)

st.subheader("Reflections")
reflections = {}
for question in REFLECTION_QUESTIONS:
    reflections[question] = st.text_area(question, height=100)

st.subheader("Video Recording")
video_file = st.file_uploader(
    "Upload your session recording", type=["mp4", "mov", "webm", "avi"]
)

if st.button("Submit Assessment", type="primary"):
    if not video_file:
        st.error("Please upload a video recording before submitting.")
        st.stop()

    empty_reflections = [q for q in REFLECTION_QUESTIONS if not reflections[q].strip()]
    if empty_reflections:
        st.warning(f"Please answer all reflection questions. Missing: {', '.join(empty_reflections)}")
        st.stop()

    os.makedirs("uploads", exist_ok=True)
    video_path = f"uploads/submission_{student_id}_round{round_num}.mp4"
    with open(video_path, "wb") as f:
        f.write(video_file.read())

    assessment = db.create_assessment(
        student_id=student_id,
        round_num=int(round_num),
        competency_ratings=json.dumps(ratings),
        reflections=json.dumps(reflections),
    )

    progress_bar = st.progress(0.0, text="Starting...")

    def update_progress(fraction: float, message: str) -> None:
        progress_bar.progress(fraction, text=message)

    try:
        processor.process_assessment(assessment["id"], video_path, progress_fn=update_progress)
        st.success("Assessment submitted successfully!")
        updated = db.get_assessment_by_id(assessment["id"])
        if updated.get("drive_folder_url"):
            st.markdown(f"[View your Drive folder]({updated['drive_folder_url']})")
    except Exception as e:
        st.error(f"Processing failed: {e}")
        st.info("Your submission was saved. Ask your admin to retry processing from the Admin page.")
```

- [ ] **Step 2: Manually test the page**

Run `streamlit run app.py`, navigate to Student Submission, and:
1. Select a student
2. Set round = 1
3. Move all sliders
4. Fill in all reflection text areas
5. Upload any small `.mp4` file
6. Click Submit

If Drive/OpenAI/Resend env vars are not set, processing should still complete (placeholders used) and show "Assessment submitted successfully!".

- [ ] **Step 3: Commit**

```bash
git add pages/1_Student_Submission.py
git commit -m "feat: student submission page with video upload and processing pipeline"
```

---

## Task 12: Mentor Review Page (`pages/2_Mentor_Review.py`)

**Files:**
- Create: `pages/2_Mentor_Review.py`

- [ ] **Step 1: Create `pages/2_Mentor_Review.py`**

```python
import sys
sys.path.insert(0, ".")
import json
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS

st.set_page_config(page_title="Mentor Review", layout="wide")
st.title("Mentor Review")

params = st.query_params
assessment_id_str = params.get("assessment_id")

if not assessment_id_str:
    st.error("No assessment ID provided. Use the link from your notification email or dashboard.")
    st.stop()

try:
    assessment_id = int(assessment_id_str)
except ValueError:
    st.error("Invalid assessment ID.")
    st.stop()

assessment = db.get_assessment_by_id(assessment_id)
if not assessment:
    st.error("Assessment not found.")
    st.stop()

student = db.get_student_by_id(assessment["student_id"])
ai_review = db.get_ai_review(assessment_id)
existing_feedback = db.get_mentor_feedback(assessment_id)

st.subheader(f"Student: {student['name']} — Round {assessment['round']}")
st.caption(f"Submitted: {assessment.get('submitted_at', 'N/A')} | Status: {assessment['status']}")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Competency Ratings")
    ratings = json.loads(assessment.get("competency_ratings") or "{}")
    for comp in COMPETENCIES:
        score = ratings.get(comp, "N/A")
        st.write(f"**{comp}:** {score}/5")

with col2:
    st.markdown("### Reflections")
    reflections = json.loads(assessment.get("reflections") or "{}")
    for question in REFLECTION_QUESTIONS:
        answer = reflections.get(question, "(no answer)")
        st.markdown(f"**{question}**")
        st.write(answer)

st.divider()
st.markdown("### Session Transcript")
transcript = assessment.get("transcript") or "(transcript not yet available)"
st.text_area("Transcript", value=transcript, height=200, disabled=True, label_visibility="collapsed")

if ai_review:
    st.divider()
    st.markdown("### AI Review (Internal)")
    st.info(ai_review["content"])

st.divider()
st.markdown("### Your Feedback")
feedback_text = st.text_area(
    "Write your feedback for the student",
    value=existing_feedback["feedback_text"] if existing_feedback else "",
    height=200,
)

if st.button("Save Feedback", type="primary"):
    if not feedback_text.strip():
        st.error("Please write feedback before saving.")
    else:
        db.save_mentor_feedback(assessment_id, feedback_text.strip())
        st.success("Feedback saved.")

if assessment.get("drive_folder_url"):
    st.markdown(f"[Open Drive Folder]({assessment['drive_folder_url']})")
if assessment.get("pdf_drive_url"):
    st.markdown(f"[View Assessment PDF]({assessment['pdf_drive_url']})")
```

- [ ] **Step 2: Manually test the page**

After submitting an assessment in Task 11, navigate to:
`http://localhost:8501/Mentor_Review?assessment_id=1`

Verify: student name, round, ratings, reflections, transcript, and AI review are displayed. Enter feedback and click Save.

- [ ] **Step 3: Commit**

```bash
git add pages/2_Mentor_Review.py
git commit -m "feat: mentor review page with assessment details and feedback form"
```

---

## Task 13: Mentor Dashboard Page (`pages/3_Mentor_Dashboard.py`)

**Files:**
- Create: `pages/3_Mentor_Dashboard.py`

- [ ] **Step 1: Create `pages/3_Mentor_Dashboard.py`**

```python
import sys
sys.path.insert(0, ".")
import os
import streamlit as st
import db

st.set_page_config(page_title="Mentor Dashboard", layout="wide")
st.title("Mentor Dashboard")

params = st.query_params
mentor_id_str = params.get("mentor_id")

if not mentor_id_str:
    st.info("Select a mentor to view their dashboard.")
    mentors = db.get_mentors()
    if not mentors:
        st.warning("No mentors found.")
        st.stop()
    mentor_map = {m["name"]: m["id"] for m in mentors}
    selected = st.selectbox("Select mentor", list(mentor_map.keys()))
    mentor_id = mentor_map[selected]
else:
    try:
        mentor_id = int(mentor_id_str)
    except ValueError:
        st.error("Invalid mentor ID.")
        st.stop()

mentor = db.get_mentor_by_id(mentor_id)
if not mentor:
    st.error("Mentor not found.")
    st.stop()

st.subheader(f"Assessments for {mentor['name']}")

assessments = db.get_assessments_by_mentor(mentor_id)
if not assessments:
    st.info("No assessments assigned yet.")
    st.stop()

app_url = os.environ.get("APP_URL", "http://localhost:8501")

for a in assessments:
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(f"**{a['student_name']}** — Round {a['round']}")
            st.caption(f"Submitted: {a.get('submitted_at', 'N/A')}")
        with col2:
            status_color = {"complete": "green", "error": "red", "processing": "orange"}.get(
                a["status"], "gray"
            )
            st.markdown(f":{status_color}[{a['status'].upper()}]")
        with col3:
            review_url = f"{app_url}/Mentor_Review?assessment_id={a['id']}"
            st.markdown(f"[Review]({review_url})")
            if a.get("drive_folder_url"):
                st.markdown(f"[Drive folder]({a['drive_folder_url']})")
```

- [ ] **Step 2: Manually test the page**

Navigate to `http://localhost:8501/Mentor_Dashboard` and select a mentor. Verify submitted assessments appear with correct status and review links.

- [ ] **Step 3: Commit**

```bash
git add pages/3_Mentor_Dashboard.py
git commit -m "feat: mentor dashboard showing assigned assessments with status and links"
```

---

## Task 14: Admin Page (`pages/4_Admin.py`)

**Files:**
- Create: `pages/4_Admin.py`

- [ ] **Step 1: Create `pages/4_Admin.py`**

```python
import sys
sys.path.insert(0, ".")
import os
import streamlit as st
import db
from services import processor

st.set_page_config(page_title="Admin", layout="wide")
st.title("Admin Dashboard")

tab_assessments, tab_mentors, tab_students = st.tabs(["Assessments", "Mentors", "Students"])

app_url = os.environ.get("APP_URL", "http://localhost:8501")

# --- Assessments Tab ---
with tab_assessments:
    st.subheader("All Assessments")

    all_assessments = db.get_all_assessments()
    if not all_assessments:
        st.info("No assessments yet.")
    else:
        status_filter = st.selectbox(
            "Filter by status",
            ["all", "submitted", "processing", "complete", "error"],
        )
        filtered = (
            all_assessments
            if status_filter == "all"
            else [a for a in all_assessments if a["status"] == status_filter]
        )

        for a in filtered:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 3])
                with col1:
                    st.markdown(f"**{a['student_name']}** (mentor: {a['mentor_name']})")
                    st.caption(f"Round {a['round']} | {a.get('submitted_at', 'N/A')}")
                with col2:
                    status_color = {"complete": "green", "error": "red", "processing": "orange"}.get(
                        a["status"], "gray"
                    )
                    st.markdown(f":{status_color}[{a['status'].upper()}]")
                    if a.get("error_message"):
                        st.caption(f"Error: {a['error_message'][:80]}")
                with col3:
                    review_url = f"{app_url}/Mentor_Review?assessment_id={a['id']}"
                    st.markdown(f"[Review]({review_url})")
                    if a["status"] == "error":
                        if st.button(f"Retry #{a['id']}", key=f"retry_{a['id']}"):
                            # Re-attempt processing (video must still exist in uploads/)
                            video_path = f"uploads/submission_{a['student_id']}_round{a['round']}.mp4"
                            if not os.path.exists(video_path):
                                st.error(f"Video file not found at {video_path}. Cannot retry.")
                            else:
                                with st.spinner("Retrying..."):
                                    try:
                                        processor.process_assessment(a["id"], video_path)
                                        st.success("Retry succeeded.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Retry failed: {e}")

# --- Mentors Tab ---
with tab_mentors:
    st.subheader("Mentors")
    mentors = db.get_mentors()
    for m in mentors:
        with st.expander(f"{m['name']} — {m['email']}"):
            with st.form(key=f"mentor_form_{m['id']}"):
                new_name = st.text_input("Name", value=m["name"])
                new_email = st.text_input("Email", value=m["email"])
                st.caption(f"Dashboard token: `{m['dashboard_token']}`")
                dashboard_url = f"{app_url}/Mentor_Dashboard?mentor_id={m['id']}"
                st.markdown(f"[Dashboard link]({dashboard_url})")
                if st.form_submit_button("Save"):
                    db.update_mentor(m["id"], new_name, new_email)
                    st.success("Saved.")
                    st.rerun()

    st.divider()
    st.markdown("#### Add Mentor")
    with st.form("add_mentor_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        if st.form_submit_button("Add Mentor"):
            if name.strip() and email.strip():
                db.add_mentor(name.strip(), email.strip())
                st.success(f"Mentor {name} added.")
                st.rerun()
            else:
                st.error("Name and email are required.")

# --- Students Tab ---
with tab_students:
    st.subheader("Students")
    students = db.get_students()
    mentors = db.get_mentors()
    mentor_map = {m["id"]: m["name"] for m in mentors}
    mentor_options = {m["name"]: m["id"] for m in mentors}

    for s in students:
        with st.expander(f"{s['name']} — mentor: {mentor_map.get(s['mentor_id'], 'unassigned')}"):
            with st.form(key=f"student_form_{s['id']}"):
                new_name = st.text_input("Name", value=s["name"])
                current_mentor_name = mentor_map.get(s["mentor_id"], list(mentor_options.keys())[0])
                new_mentor_name = st.selectbox(
                    "Mentor",
                    list(mentor_options.keys()),
                    index=list(mentor_options.keys()).index(current_mentor_name)
                    if current_mentor_name in mentor_options else 0,
                )
                if st.form_submit_button("Save"):
                    db.update_student(s["id"], new_name.strip(), mentor_options[new_mentor_name])
                    st.success("Saved.")
                    st.rerun()

    st.divider()
    st.markdown("#### Add Student")
    with st.form("add_student_form"):
        name = st.text_input("Name")
        mentor_name = st.selectbox("Mentor", list(mentor_options.keys()))
        if st.form_submit_button("Add Student"):
            if name.strip():
                db.add_student(name.strip(), mentor_options[mentor_name])
                st.success(f"Student {name} added.")
                st.rerun()
            else:
                st.error("Name is required.")
```

- [ ] **Step 2: Manually test all three admin tabs**

Navigate to `http://localhost:8501/Admin`.

- Assessments tab: verify all submitted assessments appear; test status filter.
- Mentors tab: edit Michael's email, verify it persists. Add a new test mentor.
- Students tab: add a new student assigned to Michael.

- [ ] **Step 3: Commit**

```bash
git add pages/4_Admin.py
git commit -m "feat: admin page with assessment management, mentor and student CRUD"
```

---

## Task 15: Final Smoke Test

- [ ] **Step 1: Run all unit tests**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Seed the database**

```bash
python seed.py
```

Expected: mentors and students created (or "already exists" if re-running).

- [ ] **Step 3: Full end-to-end flow**

1. `streamlit run app.py`
2. Go to Student Submission → select "Student 1" → fill all fields → upload a small `.mp4` → Submit
3. Verify progress bar advances and "Assessment submitted successfully!" appears
4. Go to Admin → Assessments → verify the assessment appears with status `complete` (or `error` if no API keys)
5. Go to Mentor Review at the URL shown in the Admin for that assessment → verify all fields display → save feedback
6. Go to Mentor Dashboard → select Michael → verify the assessment appears with a Review link

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete Streamlit mentoring assessment MVP"
```
