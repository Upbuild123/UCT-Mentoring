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
