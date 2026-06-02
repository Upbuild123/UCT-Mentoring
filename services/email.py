import os
import resend as resend_lib


def send_mentor_notification(
    mentor_email: str,
    mentor_name: str,
    student_name: str,
    round_num: int,
    video_drive_url: str,
    transcript_url: str,
    ai_review_url: str,
    mentor_review_url: str,
) -> None:
    api_key = os.environ.get("RESEND_API_KEY", "")
    email_from = os.environ.get("EMAIL_FROM", "Mentoring Program <noreply@example.com>")

    subject = f"New mentoring recording from {student_name} - Round {round_num}"
    html = f"""
<h2>New Mentoring Recording</h2>
<p>Hi {mentor_name},</p>
<p><strong>{student_name}</strong> has submitted their Round {round_num} recording.</p>
<ul>
  <li><a href="{video_drive_url}">Video recording</a></li>
  <li><a href="{transcript_url}">Transcript</a></li>
  <li><a href="{ai_review_url}">AI-generated review</a></li>
  <li><a href="{mentor_review_url}">Submit mentor feedback</a></li>
</ul>
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
