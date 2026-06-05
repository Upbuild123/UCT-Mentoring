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

    mentor_first = mentor_name.split()[0]
    subject = f"Mentoring Recording. {student_name}. Round {round_num}"
    html = f"""
<p>Hi {mentor_first},</p>
<p>There is a new mentoring recording to review from {student_name.split()[0]}.</p>
<ul>
  <li><a href="{video_drive_url}">Video recording</a></li>
  <li><a href="{transcript_url}">Transcript</a></li>
  <li><a href="{ai_review_url}">AI-generated review</a></li>
</ul>
<p>After your mentoring meeting, <a href="{mentor_review_url}">submit mentor feedback</a>.</p>
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


def send_student_confirmation(
    student_email: str,
    student_name: str,
    round_num: int,
    drive_folder_url: str,
) -> None:
    api_key = os.environ.get("RESEND_API_KEY", "")
    email_from = os.environ.get("EMAIL_FROM", "Mentoring Program <noreply@example.com>")

    first_name = student_name.split()[0]
    subject = f"Your Round {round_num} Recording Has Been Received"
    html = f"""
<p>Hi {first_name},</p>
<p>Your Round {round_num} mentoring recording has been successfully uploaded, and your mentor has been notified.</p>
<p>You can access your recording and transcript in your Google Drive <a href="{drive_folder_url}">folder</a>.</p>
"""

    if not api_key:
        print(f"[email] Would send confirmation to {student_email}: {subject}")
        return

    resend_lib.api_key = api_key
    resend_lib.Emails.send({
        "from": email_from,
        "to": student_email,
        "subject": subject,
        "html": html,
    })


def send_completion_notification(
    mentor_email: str,
    mentor_name: str,
    student_email: str,
    student_name: str,
    round_num: int,
    pdf_drive_url: str,
) -> None:
    api_key = os.environ.get("RESEND_API_KEY", "")
    email_from = os.environ.get("EMAIL_FROM", "Mentoring Program <noreply@example.com>")

    subject = f"Your Round {round_num} Assessment is Ready - {student_name}"
    html = f"""
<h2>Mentoring Assessment Complete</h2>
<p>The Round {round_num} assessment for <strong>{student_name}</strong> is now complete.</p>
<ul>
  <li><a href="{pdf_drive_url}">View Assessment PDF</a></li>
</ul>
"""

    if not api_key:
        print(f"[email] Would send completion to {mentor_email} and {student_email}: {subject}")
        return

    resend_lib.api_key = api_key
    recipients = [mentor_email]
    if student_email:
        recipients.append(student_email)
    for recipient in recipients:
        resend_lib.Emails.send({
            "from": email_from,
            "to": recipient,
            "subject": subject,
            "html": html,
        })
