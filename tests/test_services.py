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
        mock_files.permissions.return_value.create.return_value.execute.return_value = {}
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
        mock_files.permissions.return_value.create.return_value.execute.return_value = {}
        mock_files.get.return_value.execute.return_value = {
            "webViewLink": "https://drive.google.com/file/file789"
        }

        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")

        from services.drive import upload_file
        url = upload_file(str(test_file), "folder456", "recording.mp4")
        assert "drive.google.com" in url


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
        assert result == "[No API key configured]"

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
        assert result == "[No API key configured]"


class TestEmailService:
    def test_send_notification_calls_resend(self, mocker):
        mocker.patch.dict(os.environ, {
            "RESEND_API_KEY": "re_fake_key",
            "EMAIL_FROM": "test@example.com",
        })
        mock_resend = mocker.patch("services.email.resend_lib.Emails.send")

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
