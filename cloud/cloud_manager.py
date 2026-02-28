"""
cloud/cloud_manager.py
Google Drive integration for syncing memories and preferences.
Auto-syncs every 12 hours.
"""

import os
import time
import logging
import threading

logger = logging.getLogger("Makima.Cloud")

SYNC_INTERVAL = 12 * 3600  # 12 hours

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

MEMORY_DIR = "makima_memory"
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")


class CloudManager:

    def __init__(self):
        self.service = None
        self._folder_id: str | None = None
        self._init_drive()
        # Start background sync thread
        self._sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
        self._sync_thread.start()

    def _init_drive(self):
        if not GDRIVE_AVAILABLE:
            logger.warning("google-api-python-client not installed. Cloud sync disabled.")
            return
        if not os.path.exists(CREDENTIALS_FILE):
            logger.info("No Google credentials file found. Cloud sync disabled.")
            return
        try:
            creds = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE,
                scopes=["https://www.googleapis.com/auth/drive.file"],
            )
            self.service = build("drive", "v3", credentials=creds)
            logger.info("✅ Google Drive connected.")
        except Exception as e:
            logger.warning(f"Drive init failed: {e}")

    def _get_or_create_folder(self) -> str | None:
        if not self.service:
            return None
        if self._folder_id:
            return self._folder_id
        try:
            q = "name='MakimaMemory' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(q=q, fields="files(id)").execute()
            files = results.get("files", [])
            if files:
                self._folder_id = files[0]["id"]
            else:
                meta = {
                    "name": "MakimaMemory",
                    "mimeType": "application/vnd.google-apps.folder",
                }
                folder = self.service.files().create(body=meta, fields="id").execute()
                self._folder_id = folder["id"]
            return self._folder_id
        except Exception as e:
            logger.warning(f"Drive folder error: {e}")
            return None

    def _upload_file(self, local_path: str, folder_id: str) -> bool:
        try:
            fname = os.path.basename(local_path)
            # Check if file already exists
            q = f"name='{fname}' and '{folder_id}' in parents"
            existing = self.service.files().list(q=q, fields="files(id)").execute().get("files", [])

            media = MediaFileUpload(local_path, resumable=False)
            if existing:
                self.service.files().update(
                    fileId=existing[0]["id"], media_body=media
                ).execute()
            else:
                meta = {"name": fname, "parents": [folder_id]}
                self.service.files().create(body=meta, media_body=media).execute()
            return True
        except Exception as e:
            logger.warning(f"Upload failed for {local_path}: {e}")
            return False

    def sync_now(self) -> str:
        if not self.service:
            return "Cloud sync is not configured. Add your Google service account credentials."

        folder_id = self._get_or_create_folder()
        if not folder_id:
            return "Could not access Google Drive folder."

        uploaded = 0
        for fname in os.listdir(MEMORY_DIR):
            path = os.path.join(MEMORY_DIR, fname)
            if os.path.isfile(path):
                if self._upload_file(path, folder_id):
                    uploaded += 1

        return f"Synced {uploaded} memory files to Google Drive."

    def upload(self, file_path: str) -> str:
        if not self.service:
            return "Cloud sync is not configured."
        folder_id = self._get_or_create_folder()
        if not folder_id:
            return "Drive folder unavailable."
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        success = self._upload_file(file_path, folder_id)
        return f"Uploaded {os.path.basename(file_path)} to Drive." if success else "Upload failed."

    def _auto_sync_loop(self):
        while True:
            time.sleep(SYNC_INTERVAL)
            try:
                result = self.sync_now()
                logger.info(f"Auto-sync: {result}")
            except Exception as e:
                logger.warning(f"Auto-sync error: {e}")
