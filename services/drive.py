import os
from typing import Optional
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
    folder = service.files().create(
        body=meta, fields="id", supportsAllDrives=True
    ).execute()
    return folder["id"]


def _find_folder(service, name: str, parent_id: str) -> Optional[str]:
    """Return the id of an existing folder with this name under parent_id, or None."""
    query = (
        f"name = '{name}' and '{parent_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )
    result = service.files().list(
        q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    files = result.get("files", [])
    return files[0]["id"] if files else None


def _get_web_link(service, file_id: str) -> str:
    file = service.files().get(
        fileId=file_id, fields="webViewLink", supportsAllDrives=True
    ).execute()
    return file["webViewLink"]


def _share_folder(service, folder_id: str, email: str, role: str = "reader") -> None:
    """Share a folder with a specific email address."""
    service.permissions().create(
        fileId=folder_id,
        body={"type": "user", "role": role, "emailAddress": email},
        supportsAllDrives=True,
        sendNotificationEmail=False,
    ).execute()


def create_student_round_folder(student_name: str, round_num: int, student_email: str = ""):
    """
    Get or create: parent/<student_name>/Round <round_num>.
    If the student folder is newly created and student_email is provided,
    shares it with the student (viewer access).
    Returns (round_folder_id, round_folder_url).
    """
    service = _get_service()
    parent_id = os.environ["GOOGLE_DRIVE_PARENT_FOLDER_ID"]

    # Reuse existing student folder if it exists
    student_folder_id = _find_folder(service, student_name, parent_id)
    newly_created = student_folder_id is None
    if newly_created:
        student_folder_id = _create_folder(service, student_name, parent_id)

    # Share the student folder with the student on first creation
    if newly_created and student_email:
        _share_folder(service, student_folder_id, student_email, role="writer")

    round_folder_id = _create_folder(service, f"Round {round_num}", student_folder_id)
    folder_url = _get_web_link(service, round_folder_id)
    return round_folder_id, folder_url


def upload_file(local_path: str, folder_id: str, filename: str) -> str:
    """Upload a file to Drive folder and return its shareable URL."""
    service = _get_service()
    meta = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(
        body=meta, media_body=media, fields="id", supportsAllDrives=True
    ).execute()
    file_id = file["id"]
    file_url = _get_web_link(service, file_id)
    return file_url
