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


def create_student_round_folder(student_name: str, round_num: int):
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
