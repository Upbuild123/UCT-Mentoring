# Streamlit Mentoring Assessment App — Design Spec

Date: 2026-06-02

## Overview

A pure Streamlit + SQLite web app that replaces the original Node.js/TypeScript mentoring assessment system. Students submit video recordings and competency self-assessments; the app uploads the video to Google Drive, transcribes it via OpenAI, generates an AI review, notifies the mentor via email (Resend), and produces a PDF. Mentors review assessments and submit feedback. Admins manage the data and monitor status.

Processing runs synchronously on submission (with a Streamlit progress spinner), eliminating the need for a background job queue.

---

## Architecture

```
app.py                          # root landing page / redirect
pages/
  1_Student_Submission.py       # student form: video upload, ratings, reflections
  2_Mentor_Review.py            # mentor reviews one assessment (URL param: ?assessment_id=X)
  3_Mentor_Dashboard.py         # mentor's list of assigned assessments (URL param: ?mentor_id=X)
  4_Admin.py                    # admin: manage mentors, students, view assessments

db.py                           # SQLite connection + all queries (single source of truth)
services/
  drive.py                      # Google Drive: create folders, upload files, share links
  openai_service.py             # OpenAI: audio transcription + AI review generation
  email.py                      # Resend: send mentor notification emails
  pdf.py                        # PDF generation (fpdf2 or reportlab)
  processor.py                  # Orchestrates full pipeline after submission

uploads/                        # Temp staging for video before Drive upload (auto-deleted)
data/
  mentoring.db                  # SQLite database file
```

**No background job queue.** Processing is triggered on form submission and runs to completion before the confirmation screen is shown. This simplifies the architecture significantly at the cost of a longer wait on the submission page for large videos.

---

## Data Models

### mentors
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| email | TEXT | |
| dashboard_token | TEXT | unique, used in dashboard URL |

### students
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| mentor_id | INTEGER FK | references mentors.id |

### assessments
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| student_id | INTEGER FK | |
| round | INTEGER | mentoring round number |
| video_drive_url | TEXT | shareable Drive link to video |
| transcript | TEXT | OpenAI transcription output |
| competency_ratings | TEXT | JSON blob of rating values |
| reflections | TEXT | JSON blob of reflection text answers |
| status | TEXT | submitted / processing / complete / error |
| student_token | TEXT | unique, used in submission summary URL |
| mentor_token | TEXT | unique, used in mentor review URL |
| drive_folder_url | TEXT | shareable Drive folder link |
| pdf_drive_url | TEXT | shareable Drive link to PDF |
| submitted_at | DATETIME | |

### ai_reviews
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| assessment_id | INTEGER FK | |
| content | TEXT | raw AI review text |
| created_at | DATETIME | |

### mentor_feedback
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| assessment_id | INTEGER FK | |
| feedback_text | TEXT | |
| submitted_at | DATETIME | |

---

## Processing Pipeline

Triggered synchronously on student form submission. Runs in `processor.py` and displays progress via a Streamlit `st.progress` bar.

1. Save assessment record to SQLite (status: `processing`)
2. Upload video to Google Drive (create per-student, per-round folder)
3. Extract audio from video (ffmpeg) → save temp audio file
4. Transcribe audio via OpenAI Whisper API
5. Delete temp audio file
6. Delete local temp video file
7. Generate AI review via OpenAI
8. Generate PDF (student ratings + reflections + transcript + AI review)
9. Upload PDF to Google Drive
10. Send mentor notification email via Resend (includes Drive links, mentor review URL)
11. Update assessment record (status: `complete`, all Drive URLs, transcript)

If any step fails, status is set to `error` and the error message is displayed. Admin can view the error and re-trigger processing.

---

## Pages

### 1. Student Submission (`pages/1_Student_Submission.py`)
- Dropdown to select student name
- Round number input
- Competency rating sliders/selectors (replicating original competency fields)
- Reflection text areas
- Video file uploader (`st.file_uploader`, accepts mp4/mov/webm)
- Submit button → runs full pipeline with progress bar
- On success: confirmation message with Drive folder link

### 2. Mentor Review (`pages/2_Mentor_Review.py`)
- URL param: `?assessment_id=X`
- Displays: student name, round, submitted date, competency ratings, reflections, transcript, AI review
- Text area for mentor feedback
- Submit button → saves `mentor_feedback`, triggers PDF regeneration if needed
- Confirmation on save

### 3. Mentor Dashboard (`pages/3_Mentor_Dashboard.py`)
- URL param: `?mentor_id=X`
- Table of all assessments assigned to that mentor
- Columns: student name, round, status, submitted date, link to review page

### 4. Admin (`pages/4_Admin.py`)
- Tab 1 — **Assessments**: filterable table of all assessments; status badge; link to mentor review; re-trigger processing button for errored assessments
- Tab 2 — **Mentors**: table of mentors; add new mentor form (name, email); edit email
- Tab 3 — **Students**: table of students with assigned mentor; add student form; reassign mentor dropdown

---

## Seeding

`seed.py` — standalone script that inserts initial data if not already present (idempotent upserts):
- Mentors: Michael (michael@upbuild.com), Vipin (vipin@example.com)
- Students: Student 1 → Michael, Student 2 → Vipin

Run once at setup: `python seed.py`

---

## External Services

### Google Drive (`services/drive.py`)
- Auth via service account (`GOOGLE_CLIENT_EMAIL` + `GOOGLE_PRIVATE_KEY`)
- Creates folder hierarchy: `<parent>/<student_name>/<round>/`
- Uploads video and PDF; returns shareable links
- Private key normalized to handle `\n` vs `\\n` in env

### OpenAI (`services/openai_service.py`)
- Transcription: Whisper API on extracted audio file
- AI review: Chat Completions (or Responses API) with assessment context as prompt
- If `OPENAI_API_KEY` not set: returns placeholder text, pipeline continues

### Email (`services/email.py`)
- Resend API for mentor notification
- Email includes: student name, round, Drive folder link, video link, transcript link, mentor review URL
- If `RESEND_API_KEY` not set: logs to console instead

### PDF (`services/pdf.py`)
- Library: `fpdf2` (pure Python, no system dependencies)
- Contains: student name, round, competency ratings, reflections, transcript, AI review
- Uploaded to Drive after generation; local copy deleted

---

## Environment Variables

```
DATABASE_URL=data/mentoring.db
OPENAI_API_KEY=
RESEND_API_KEY=
GOOGLE_DRIVE_PARENT_FOLDER_ID=
GOOGLE_CLIENT_EMAIL=
GOOGLE_PRIVATE_KEY=
EMAIL_FROM=
APP_URL=http://localhost:8501
```

---

## Authentication

None for MVP. All pages are accessible to anyone with the URL. Mentor and admin pages rely on obscurity of IDs/tokens in the URL.

---

## How to Run

```bash
pip install -r requirements.txt
python seed.py          # initialize DB and seed data
streamlit run app.py    # start the app
```

---

## Out of Scope (MVP)

- Authentication / login
- Background job queue / retry logic
- Email notifications to students
- Retention / cleanup of old Drive files
- Unit or integration tests
