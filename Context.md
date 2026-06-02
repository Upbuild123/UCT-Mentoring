Project: Mentoring Assessment MVP

Overview

This repository is a minimal mentoring assessment web app (MVP) that supports one student submission per mentoring round and asynchronous processing to produce transcripts, AI reviews, and PDFs. The app stores records in SQLite (Prisma), uploads artifacts to Google Drive (service account), sends notifications via Resend, and uses OpenAI for transcription and AI review (if API keys are configured).

Primary goals achieved

- Student + Round → one Assessment record
- Student submission page with video upload, competency ratings, and reflections
- Background processing queue: extract audio → transcribe → upload to Drive → notify mentor → AI review → generate PDF
- Mentor review page (secure token link) and mentor dashboard (dashboard token)
- Admin dashboard with filtering, retry processing, and resend notification actions

Tech stack

- Node.js + TypeScript
- Express + EJS views
- Prisma ORM with SQLite (local) for data
- ffmpeg (fluent-ffmpeg) for audio extraction from video
- OpenAI (audio transcription + AI review) — optional (requires `OPENAI_API_KEY`)
- Google Drive via `googleapis` using a service account
- Resend for email delivery (replaced Nodemailer)
- PDF generation with PDFKit

Key repository files and locations

- `src/index.ts` — app entry (loads env and starts server)
- `src/app.ts` — main Express app (registers routers)
- `src/routes/student.ts` — student submission routes and form handling
- `src/routes/mentor.ts` — mentor review route + save feedback + PDF generation
- `src/routes/mentorDashboard.ts` — mentor dashboard (token-based)
- `src/routes/admin.ts` — admin status/filter/retry/resend actions
- `src/services/jobQueue.ts` — background queue: extraction, transcription, uploads, notification, AI review
- `src/services/transcriptionService.ts` — audio extraction and OpenAI transcription wrapper
- `src/services/aiService.ts` — calls OpenAI for internal AI review (saves internal-only record)
- `src/services/driveService.ts` — Google Drive service-account integration
- `src/services/emailService.ts` — Resend integration for sending mentor/student emails
- `src/services/pdfService.ts` — PDF generation helper (PDFKit)
- `src/templates/` — EJS templates for `studentSubmission`, `mentorReview`, `mentorDashboard`, `adminStatus`, and summary pages
- `public/styles.css` — main CSS (student submission spacing updated)
- `prisma/schema.prisma` — schema of `Student`, `Mentor`, `Assessment`, `ProcessingJob`, `AIReview`, etc.
- `prisma/seed.ts` (and compiled `seed.js`) — seeds mentors and students; updated so Michael mentors `Student 1` and Vipin mentors `Student 2` and Michael's email is `michael@upbuild.com`.
- `prisma/dev.db` — seeded SQLite DB used by the project (note: ensure `DATABASE_URL` points to `file:./prisma/dev.db`)

Routes (quick reference)

- `/` — student submission form
- `/submit` (POST) — student submission endpoint (multipart form upload)
- `/submission/:studentToken` — student submission summary
- `/mentor/:mentorToken` — mentor review page (token-protected)
- `/mentor-dashboard/:dashboardToken` — mentor dashboard (list of assigned assessments)
- `/admin` — admin status and job list

Important runtime configuration (`.env`)

Required/Recommended environment variables (local `.env`):

- `DATABASE_URL` — set to `file:./prisma/dev.db` for local seeded DB
- `PORT` — optional (default 4000)
- `APP_URL` — url for links (default http://localhost:4000)
- `OPENAI_API_KEY` — (optional) OpenAI key for transcription and AI review
- `RESEND_API_KEY` — (optional) Resend API key for emails (if not set, email actions are logged to console)
- `GOOGLE_DRIVE_PARENT_FOLDER_ID` — Drive folder id where student folders will be created
- `GOOGLE_CLIENT_EMAIL` — service account client email
- `GOOGLE_PRIVATE_KEY` — service account private key (PEM). See formatting notes below.
- `EMAIL_FROM` — sender address (e.g. "Mentoring Program <noreply@example.com>")

Do NOT store or share your secret keys publicly. Keep `.env` local.

Formatting note for `GOOGLE_PRIVATE_KEY`:

- `src/services/driveService.ts` uses `normalizePrivateKey()` which calls `raw.replace(/\\n/g, '\n')` to allow either:
  - storing the private key in `.env` with literal `\n` sequences, e.g. `GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nMII...\\n-----END PRIVATE KEY-----"`
  - or storing it with newline characters inside quotes if your environment supports it. If you get JWT/OpenSSL signing errors (see Known Issues), try switching formats.

How to run locally

1. Install dependencies:

```bash
npm install
```

2. Ensure `.env` is present and filled with appropriate values (see keys above). For local testing, you can leave optional keys blank; the app will fall back to no-op behavior for email/AI/Drive.

3. If you need the seeded test data, ensure `DATABASE_URL` points to `file:./prisma/dev.db` then run (only if you need to re-seed):

```bash
npm run prisma:seed
```

4. Start the dev server:

```bash
npm run dev
```

5. Open the app in your browser:

- `http://localhost:4000/` — student submission
- `http://localhost:4000/admin` — admin dashboard

Background processing

- When a student submits a video, the submission is saved and `processAssessment()` (in `src/services/jobQueue.ts`) is enqueued.
- Jobs run sequentially: AUDIO_EXTRACTION → TRANSCRIPTION → NOTIFICATION → generate AI review → PDF generation
- Each job creates a `ProcessingJob` record and updates the `Assessment.status` and various Drive fields on success.

Email/Notifications

- Emails are sent using Resend (replace Nodemailer). If `RESEND_API_KEY` is not configured, the app logs the intended email content to the console instead of sending.
- Mentor notifications include: recording link, transcript link, folder link, student submission link, mentor review link, and optional dashboard link.

Google Drive integration

- Creates folders per student and per round under `GOOGLE_DRIVE_PARENT_FOLDER_ID`.
- Uploads recording, transcript, and PDF files into the round folder and makes them shareable.
- Requires a Google service account with Drive access to the parent folder.

OpenAI integration

- If `OPENAI_API_KEY` is set: transcribes audio via the `openai` package (transcription) and generates internal AI reviews (responses API).
- If not set, transcription and AI review functions return placeholders and the flow still proceeds (but transcripts are placeholder text).

PDF generation

- Mentors can finalize reviews which triggers PDF generation via PDFKit and uploads the resulting PDF to Drive (if drive is configured).

Seeding and sample data

- `prisma/seed.ts` seeds mentors and students. Current seeded mentors include `Michael` (email `michael@upbuild.com`) and `Vipin` (`vipin@example.com`).
- Sample students are `Student 1` (mentor Michael) and `Student 2` (mentor Vipin).
- If you need to inspect or query tokens and records directly, `prisma/dev.db` contains the data; example queries using `sqlite3` were used during development.

Known issues & troubleshooting

1. ffmpeg "unsupported decoder" errors
   - If the background job fails at audio extraction with a decoder error, ensure you have a full `ffmpeg` installed (Homebrew `brew install ffmpeg` on macOS) and the uploaded MP4 uses standard codecs (H.264 video, AAC audio).
   - You can convert a problematic video with:

```bash
ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4
```

2. Google service account / JWT OpenSSL errors
   - If you see `ERR_OSSL_UNSUPPORTED` or OpenSSL decoding errors when Drive auth runs, it usually means the private key is not parsed correctly. Try adjusting the `GOOGLE_PRIVATE_KEY` formatting in `.env` (use `\n` sequences or ensure the key is quoted). `src/utils.normalizePrivateKey` will convert `\\n` to newlines.
   - Ensure the service account has permission to the `GOOGLE_DRIVE_PARENT_FOLDER_ID` (share the folder with the service account email if needed).

3. Environment variables not loaded
   - The app now uses `dotenv` (loaded in `src/index.ts`) so `.env` values are available at runtime. If you modify `.env` while `ts-node-dev` is running, restart the server.

4. Database file location
   - The app uses `DATABASE_URL` in `.env`. During development we use the seeded DB at `prisma/dev.db`. If you see an empty `dev.db` at the repo root, update `DATABASE_URL` to `file:./prisma/dev.db`.

Recent changes (high level)

- Added mentor dashboard links to admin UI and a `mentorDashboard` route/view.
- Seeded Michael and Vipin mentors; updated Michael's email to `michael@upbuild.com`.
- Switched email delivery to `resend` and removed Nodemailer from active flow.
- Ensured Drive service uses a Google service account (`GOOGLE_CLIENT_EMAIL` + `GOOGLE_PRIVATE_KEY`) and added normalize helper.
- Added `dotenv` loading at startup.
- Improved student submission page layout and CSS for cleaner spacing and section cards.
- Added robust fallbacks so the app can start without external API keys (logs instead of failing hard).

Developer notes & quick queries

- To list mentors (sqlite):

```bash
sqlite3 prisma/dev.db "SELECT id, name, email, dashboardToken FROM Mentor;"
```

- To list assessments and recent processing jobs:

```bash
sqlite3 prisma/dev.db "SELECT id, studentToken, mentorToken, round, status FROM Assessment;"
sqlite3 prisma/dev.db "SELECT id, assessmentId, type, status, startedAt, finishedAt, errorMessage FROM ProcessingJob ORDER BY startedAt DESC LIMIT 20;"
```

- To run seed (idempotent upserts):

```bash
npm run prisma:seed
```

Next recommended enhancements

- Add clearer UI status for processing steps on the student and admin pages (more verbose job error messages and retry hints)
- Add authentication for mentors and admins instead of token-only links
- Improve mentor dashboard layout and add bulk actions
- Add retention/cleanup for old uploads and Drive files
- Add unit/integration tests for the background job flow and Drive interactions (use a mock Drive in CI)

Contact / Ownership

- This file summarizes the current state of the workspace as of the latest edits.
- If you need the file tailored to a particular format required by Claude Code, tell me which sections to expand or compress.

----
Generated by an assistant while working in the repository to capture the development context and recent edits. Do NOT include any secrets from your `.env` when sharing this file externally.
