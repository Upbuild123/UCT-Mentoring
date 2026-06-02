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
