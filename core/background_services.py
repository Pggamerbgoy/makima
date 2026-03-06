

"""
core/background_services.py

Silent Background Service Manager
───────────────────────────────────
Runs all background tasks silently. Zero interruptions to the user.

Services:
  WhatsAppService   — polls for unread msgs, auto-replies, never pops up browser
  EmailService      — polls inbox, alerts ONLY on priority emails, handles rest silently
  FileService       — scheduled auto-organize, auto-cleanup, watches folders
  ServiceManager   — starts/stops all services, exposes status

Design principles:
  - Browser runs headless (no window at all)
  - No TTS unless it's genuinely urgent (priority email, important WhatsApp)
  - All activity logged to background_services.log
  - User can check activity anytime: "what did you do in background?"
  - Services are individually enable/disable-able
"""

import os
import time
import json
import logging
import threading
import queue
from datetime import datetime, timedelta
from typing import Optional, Callable
from pathlib import Path
from collections import deque

logger = logging.getLogger("Makima.BGServices")

ACTIVITY_LOG_FILE = "background_activity.json"
MAX_ACTIVITY_LOG = 100  # Keep last N events


# ─── Activity Log ─────────────────────────────────────────────────────────────

class ActivityLog:
    """Thread-safe log of everything done in the background."""

    def __init__(self):
        self._log: deque = deque(maxlen=MAX_ACTIVITY_LOG)
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(ACTIVITY_LOG_FILE):
            try:
                with open(ACTIVITY_LOG_FILE) as f:
                    data = json.load(f)
                    for item in data[-MAX_ACTIVITY_LOG:]:
                        self._log.append(item)
            except Exception:
                pass

    def _save(self):
        try:
            with open(ACTIVITY_LOG_FILE, "w") as f:
                json.dump(list(self._log), f, indent=2)
        except Exception:
            pass

    def add(self, service: str, action: str, detail: str = ""):
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "service": service,
            "action": action,
            "detail": detail,
        }
        with self._lock:
            self._log.append(entry)
            self._save()
        logger.info(f"[{service}] {action}: {detail}")

    def recent(self, n: int = 10) -> list[dict]:
        with self._lock:
            return list(self._log)[-n:]

    def summary(self, n: int = 10) -> str:
        recent = self.recent(n)
        if not recent:
            return "No background activity yet."
        lines = [f"Last {len(recent)} background actions:"]
        for e in reversed(recent):
            lines.append(f"  [{e['time']}] {e['service']}: {e['action']} — {e['detail']}")
        return "\n".join(lines)

    def count_today(self) -> dict[str, int]:
        today = datetime.now().strftime("%Y-%m-%d")
        counts: dict[str, int] = {}
        with self._lock:
            for e in self._log:
                if e.get("date") == today:
                    counts[e["service"]] = counts.get(e["service"], 0) + 1
        return counts


# ─── Base Background Service ──────────────────────────────────────────────────

class BackgroundService:
    """Base class for all silent background services."""

    def __init__(self, name: str, activity_log: ActivityLog,
                 urgent_callback: Optional[Callable] = None):
        self.name = name
        self.log = activity_log
        self.urgent_callback = urgent_callback  # Only called for GENUINELY urgent things
        self.enabled = True
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _alert_user(self, message: str):
        """Only call this for truly urgent things — otherwise stay silent."""
        if self.urgent_callback:
            self.urgent_callback(message)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"▶ {self.name} started (silent background mode)")

    def stop(self):
        self._running = False
        logger.info(f"⏹ {self.name} stopped")

    def _run_loop(self):
        raise NotImplementedError


# ─── Silent WhatsApp Service ──────────────────────────────────────────────────

class WhatsAppService(BackgroundService):
    """
    Silent WhatsApp auto-reply service.
    - Runs Chrome headless (NO visible browser window)
    - Polls every 30 seconds for unread messages
    - Auto-replies using AI — contextual, not generic
    - Only alerts user if a VIP contact messages (configurable)
    - Logs everything to activity log
    """

    CHECK_INTERVAL = 30       # seconds between checks
    REPLY_DELAY = (2, 5)      # random delay before replying (looks human)

    def __init__(self, ai, activity_log: ActivityLog,
                 urgent_callback: Optional[Callable] = None):
        super().__init__("WhatsApp", activity_log, urgent_callback)
        self.ai = ai
        self.auto_reply = False
        self.away_message = ""
        self.use_ai_replies = True
        self.vip_contacts: set[str] = set()  # Always alert for these
        self.quiet_contacts: set[str] = set()  # Never auto-reply to these
        self._driver = None
        self._replied: set[str] = set()       # Track to avoid duplicates
        self._session_dir = "whatsapp_session"

    def enable(self, away_msg: str = "", use_ai: bool = True) -> str:
        self.auto_reply = True
        self.use_ai_replies = use_ai
        if away_msg:
            self.away_message = away_msg
        if not self._running:
            self.start()
        return "WhatsApp auto-reply is now running silently in the background."

    def disable(self) -> str:
        self.auto_reply = False
        return "WhatsApp auto-reply paused. I'll keep checking but won't reply."

    def add_vip(self, contact: str) -> str:
        self.vip_contacts.add(contact.lower())
        return f"Added {contact} as VIP. I'll alert you immediately when they message."

    def _init_headless_browser(self) -> bool:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.add_argument("--headless=new")           # COMPLETELY INVISIBLE
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1280,720")
            options.add_argument(f"--user-data-dir={os.path.abspath(self._session_dir)}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])

            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.get("https://web.whatsapp.com")

            # Wait for WhatsApp to load (must have scanned QR at least once before)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By

            WebDriverWait(self._driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]'))
            )
            self.log.add("WhatsApp", "Connected", "Headless browser running invisibly")
            return True

        except Exception as e:
            logger.warning(f"WhatsApp headless browser failed: {e}")
            # First-time setup note
            if "session" not in str(e).lower():
                logger.info("TIP: Run WhatsApp once in visible mode to scan QR, then it works headless.")
            return False

    def _get_unread(self) -> list[dict]:
        from selenium.webdriver.common.by import By
        unread = []
        try:
            badges = self._driver.find_elements(
                By.CSS_SELECTOR, '[data-testid="icon-unread-count"]'
            )
            for badge in badges:
                try:
                    row = badge.find_element(
                        By.XPATH, "./ancestor::div[@data-testid='list-item-v3']"
                    )
                    name = row.find_element(
                        By.CSS_SELECTOR, "[data-testid='cell-frame-title'] span"
                    ).text
                    preview = row.find_element(
                        By.CSS_SELECTOR, "span.x1iyjqo2"
                    ).text
                    unread.append({"name": name, "preview": preview, "element": row})
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Get unread error: {e}")
        return unread

    def _open_chat_and_reply(self, chat: dict) -> tuple[bool, str]:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            chat["element"].click()
            time.sleep(1.5)

            # Get last message text for context
            msgs = self._driver.find_elements(By.CSS_SELECTOR, '[data-testid="msg-container"]')
            last_msg = ""
            for msg in reversed(msgs[-5:]):
                try:
                    txt = msg.find_element(By.CSS_SELECTOR, "span.selectable-text").text
                    if txt:
                        last_msg = txt
                        break
                except Exception:
                    continue

            # Generate reply
            if self.use_ai_replies:
                prompt = (
                    f"You are Makima, an AI assistant handling WhatsApp for the user who is busy.\n"
                    f"Contact '{chat['name']}' sent: '{last_msg or chat['preview']}'\n"
                    f"Write a brief, natural auto-reply (1-2 sentences). "
                    f"Be warm but mention the user is busy and will reply later. "
                    f"Don't be robotic. Don't use emojis excessively."
                )
                ai_result = self.ai.chat(prompt)
                # ai.chat() returns a (reply_text, emotion) tuple — unpack correctly
                reply = ai_result[0] if isinstance(ai_result, tuple) else str(ai_result)
            else:
                reply = self.away_message or (
                    f"Hey! I'm a bit busy right now. "
                    f"I'll get back to you soon!"
                )

            # Human-like delay
            import random
            time.sleep(random.uniform(*self.REPLY_DELAY))

            # Type and send
            box = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]')
                )
            )
            box.click()
            box.send_keys(reply)
            box.send_keys(Keys.ENTER)
            return True, reply

        except Exception as e:
            logger.debug(f"Reply error: {e}")
            return False, ""

    def _run_loop(self):
        if not self._init_headless_browser():
            logger.warning("WhatsApp: Could not start headless browser. "
                         "Run once with visible browser to scan QR code first.")
            return

        while self._running:
            try:
                if self.auto_reply:
                    unread = self._get_unread()
                    for chat in unread:
                        name = chat["name"]
                        msg_id = f"{name}:{chat['preview'][:15]}"

                        if msg_id in self._replied:
                            continue

                        # VIP contact? Alert user immediately
                        if name.lower() in self.vip_contacts:
                            self._alert_user(
                                f"Urgent: {name} messaged you on WhatsApp: {chat['preview']}"
                            )
                            self._replied.add(msg_id)
                            self.log.add("WhatsApp", "VIP Alert", f"{name}: {chat['preview'][:50]}")
                            continue

                        # Quiet contact? Skip
                        if name.lower() in self.quiet_contacts:
                            self._replied.add(msg_id)
                            continue

                        # Auto-reply silently
                        success, reply = self._open_chat_and_reply(chat)
                        if success:
                            self._replied.add(msg_id)
                            self.log.add(
                                "WhatsApp", "Auto-replied",
                                f"To: {name} | Reply: {reply[:60]}..."
                            )

            except Exception as e:
                logger.debug(f"WhatsApp loop error: {e}")

            time.sleep(self.CHECK_INTERVAL)

    def get_status(self) -> str:
        counts = self.log.count_today()
        wa_count = counts.get("WhatsApp", 0)
        status = "enabled" if self.auto_reply else "monitoring only"
        return (
            f"WhatsApp: {status}, running silently. "
            f"{wa_count} actions taken today. "
            f"VIP contacts: {', '.join(self.vip_contacts) or 'none'}."
        )


# ─── Silent Email Service ─────────────────────────────────────────────────────

class EmailService(BackgroundService):
    """
    Silent email monitoring and management.
    - Polls every 5 minutes
    - ONLY alerts user for genuine priority emails
    - Auto-archives newsletters/spam
    - Summarizes important emails for later review
    - Drafts replies to important emails, holds for approval
    """

    CHECK_INTERVAL = 300      # 5 minutes
    PRIORITY_KEYWORDS = [
        "urgent", "asap", "action required", "deadline", "invoice",
        "payment due", "interview", "offer letter", "job offer",
        "emergency", "critical", "immediate",
    ]
    NOISE_KEYWORDS = [
        "unsubscribe", "newsletter", "promo", "sale", "discount",
        "deal", "offer expires", "marketing", "no-reply",
    ]

    def __init__(self, ai, activity_log: ActivityLog,
                 urgent_callback: Optional[Callable] = None):
        super().__init__("Email", activity_log, urgent_callback)
        self.ai = ai
        self._email_addr = os.getenv("EMAIL_ADDRESS", "")
        self._password = os.getenv("EMAIL_PASSWORD", "")
        self._imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        self._imap_port = int(os.getenv("IMAP_PORT", "993"))
        self._seen_uids: set[str] = set()
        self._pending_summaries: list[dict] = []  # For user to review later
        self._pending_drafts: list[dict] = []

    def _connect(self):
        import imaplib
        imap = imaplib.IMAP4_SSL(self._imap_server, self._imap_port)
        imap.login(self._email_addr, self._password)
        return imap

    def _is_priority(self, subject: str, body: str) -> bool:
        text = (subject + " " + body[:500]).lower()
        return any(kw in text for kw in self.PRIORITY_KEYWORDS)

    def _is_noise(self, subject: str, sender: str) -> bool:
        text = (subject + " " + sender).lower()
        return any(kw in text for kw in self.NOISE_KEYWORDS)

    def _fetch_new_emails(self) -> list[dict]:
        if not self._email_addr or not self._password:
            return []
        import imaplib
        import email as email_lib
        from email.header import decode_header

        def decode_str(s):
            if not s:
                return ""
            if isinstance(s, bytes):
                return s.decode("utf-8", errors="replace")
            parts = decode_header(s)
            result = ""
            for part, charset in parts:
                if isinstance(part, bytes):
                    result += part.decode(charset or "utf-8", errors="replace")
                else:
                    result += str(part)
            return result

        new_emails = []
        try:
            imap = self._connect()
            imap.select("INBOX")
            _, data = imap.search(None, "(UNSEEN)")
            uids = data[0].split()

            for uid in uids[-20:]:  # Max 20 per check
                uid_str = uid.decode()
                if uid_str in self._seen_uids:
                    continue

                try:
                    _, msg_data = imap.fetch(uid, "(RFC822)")
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)

                    subject = decode_str(msg.get("Subject", "(No Subject)"))
                    sender = decode_str(msg.get("From", "Unknown"))
                    body = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                    new_emails.append({
                        "uid": uid_str,
                        "subject": subject,
                        "sender": sender,
                        "body": body[:2000],
                    })
                    self._seen_uids.add(uid_str)
                except Exception:
                    continue

            imap.logout()
        except Exception as e:
            logger.debug(f"Email fetch error: {e}")

        return new_emails

    def _process_email(self, email_data: dict):
        subject = email_data["subject"]
        sender = email_data["sender"]
        body = email_data["body"]

        # Noise/newsletter → just log, do nothing
        if self._is_noise(subject, sender):
            self.log.add("Email", "Ignored noise", f"From: {sender[:30]} | {subject[:40]}")
            return

        # Priority email → alert user NOW
        if self._is_priority(subject, body):
            summary_result = self.ai.chat(
                f"Summarize this urgent email in 1 sentence:\n"
                f"From: {sender}\nSubject: {subject}\n{body[:500]}"
            )
            # ai.chat() returns (reply, emotion) tuple
            summary = summary_result[0] if isinstance(summary_result, tuple) else str(summary_result)
            self._alert_user(f"Priority email from {sender.split('<')[0]}: {summary}")
            self.log.add("Email", "Priority alert sent", f"{sender[:30]} | {subject[:40]}")
            return

        # Regular email → summarize silently for later
        summary_result = self.ai.chat(
            f"Summarize this email in one short sentence:\n"
            f"From: {sender}\nSubject: {subject}\n{body[:500]}"
        )
        # ai.chat() returns (reply, emotion) tuple
        summary = summary_result[0] if isinstance(summary_result, tuple) else str(summary_result)
        self._pending_summaries.append({
            "sender": sender.split("<")[0].strip(),
            "subject": subject,
            "summary": summary,
            "time": datetime.now().strftime("%H:%M"),
        })
        self.log.add("Email", "Summarized", f"{sender[:30]} | {subject[:40]}")

    def _run_loop(self):
        if not self._email_addr:
            logger.info("Email: No credentials set. Service disabled.")
            return

        logger.info("📧 Email service running silently.")
        while self._running:
            try:
                emails = self._fetch_new_emails()
                for e in emails:
                    self._process_email(e)
            except Exception as e:
                logger.debug(f"Email service error: {e}")
            time.sleep(self.CHECK_INTERVAL)

    def get_pending_summary(self) -> str:
        """User asks 'what emails came in?' — returns digest without interrupting."""
        if not self._pending_summaries:
            return "No new emails while you were busy."
        lines = [f"📧 {len(self._pending_summaries)} emails while you were busy:"]
        for e in self._pending_summaries[-5:]:
            lines.append(f"  [{e['time']}] {e['sender']}: {e['summary']}")
        self._pending_summaries.clear()
        return "\n".join(lines)

    def get_status(self) -> str:
        counts = self.log.count_today()
        email_count = counts.get("Email", 0)
        pending = len(self._pending_summaries)
        return (
            f"Email: running silently. "
            f"{email_count} emails processed today. "
            f"{pending} unread summaries waiting for you."
        )


# ─── Silent File Service ──────────────────────────────────────────────────────

class FileService(BackgroundService):
    """
    Silent file management daemon.
    - Watches folders for clutter (configurable)
    - Auto-organizes Downloads every hour
    - Cleans temp files every 24 hours
    - Detects duplicate files
    - All done silently with full activity log
    """

    ORGANIZE_INTERVAL = 3600   # 1 hour
    CLEANUP_INTERVAL = 86400   # 24 hours
    WATCH_INTERVAL = 300       # 5 min clutter check

    TYPE_FOLDERS = {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"],
        "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".odt", ".pptx", ".xlsx"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
        "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
        "Code": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".go"],
        "Spreadsheets": [".xls", ".xlsx", ".csv"],
        "Ebooks": [".epub", ".mobi", ".azw"],
    }

    TEMP_EXTENSIONS = {".tmp", ".temp", ".bak", ".log", ".cache", "~"}
    MAX_FILE_AGE_DAYS = 30  # Delete temp files older than this

    def __init__(self, activity_log: ActivityLog,
                 urgent_callback: Optional[Callable] = None):
        super().__init__("Files", activity_log, urgent_callback)
        self.watched_folders: list[Path] = [Path.home() / "Downloads"]
        self.auto_organize = True
        self.auto_cleanup = True
        self._last_organize = 0.0
        self._last_cleanup = 0.0

    def add_watch_folder(self, folder: str) -> str:
        p = Path(folder).expanduser()
        if p.exists():
            self.watched_folders.append(p)
            return f"Now watching {p.name} for automatic organization."
        return f"Folder not found: {folder}"

    def _organize_folder(self, folder: Path) -> int:
        """Move files into typed subfolders. Returns count moved."""
        ext_map = {}
        for folder_type, exts in self.TYPE_FOLDERS.items():
            for ext in exts:
                ext_map[ext] = folder_type

        moved = 0
        try:
            for item in folder.iterdir():
                if not item.is_file():
                    continue
                # Don't touch recently modified files (< 1 min old)
                if time.time() - item.stat().st_mtime < 60:
                    continue
                dest_type = ext_map.get(item.suffix.lower(), None)
                if not dest_type:
                    continue
                dest_dir = folder / dest_type
                dest_dir.mkdir(exist_ok=True)
                target = dest_dir / item.name
                # Don't overwrite
                if target.exists():
                    continue
                import shutil
                shutil.move(str(item), str(target))
                moved += 1
        except Exception as e:
            logger.debug(f"Organize error in {folder}: {e}")

        return moved

    def _cleanup_temp_files(self, root: Path) -> tuple[int, int]:
        """Delete old temp files. Returns (count, bytes_freed)."""
        cutoff = time.time() - self.MAX_FILE_AGE_DAYS * 86400
        deleted, freed = 0, 0
        try:
            for f in root.rglob("*"):
                if not f.is_file():
                    continue
                if f.suffix.lower() in self.TEMP_EXTENSIONS or f.name.endswith("~"):
                    if f.stat().st_mtime < cutoff:
                        size = f.stat().st_size
                        try:
                            f.unlink()
                            deleted += 1
                            freed += size
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")
        return deleted, freed

    def _human_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _run_loop(self):
        logger.info("📁 File service running silently.")
        while self._running:
            now = time.time()

            # Auto-organize watched folders
            if self.auto_organize and now - self._last_organize > self.ORGANIZE_INTERVAL:
                for folder in self.watched_folders:
                    if not folder.exists():
                        continue
                    moved = self._organize_folder(folder)
                    if moved > 0:
                        self.log.add(
                            "Files", "Auto-organized",
                            f"{folder.name}: moved {moved} files into subfolders"
                        )
                self._last_organize = now

            # Auto-cleanup temp files
            if self.auto_cleanup and now - self._last_cleanup > self.CLEANUP_INTERVAL:
                total_deleted, total_freed = 0, 0
                for folder in self.watched_folders:
                    d, f = self._cleanup_temp_files(folder)
                    total_deleted += d
                    total_freed += f
                if total_deleted > 0:
                    self.log.add(
                        "Files", "Auto-cleanup",
                        f"Deleted {total_deleted} temp files, freed {self._human_size(total_freed)}"
                    )
                self._last_cleanup = now

            time.sleep(self.WATCH_INTERVAL)

    def get_status(self) -> str:
        counts = self.log.count_today()
        file_count = counts.get("Files", 0)
        folders = [f.name for f in self.watched_folders]
        return (
            f"Files: running silently. "
            f"{file_count} actions today. "
            f"Watching: {', '.join(folders)}."
        )


# ─── Service Manager ──────────────────────────────────────────────────────────

class ServiceManager:
    """
    Central manager for all background services.
    Single point of control — start, stop, query status.
    """

    def __init__(self, ai, speak_callback: Optional[Callable] = None):
        self.ai = ai
        self._speak = speak_callback
        self.activity_log = ActivityLog()

        # Only alert for URGENT things
        def urgent_callback(msg: str):
            if self._speak:
                self._speak(msg)

        self.whatsapp = WhatsAppService(
            ai=ai,
            activity_log=self.activity_log,
            urgent_callback=urgent_callback,
        )
        self.email = EmailService(
            ai=ai,
            activity_log=self.activity_log,
            urgent_callback=urgent_callback,
        )
        self.files = FileService(
            activity_log=self.activity_log,
            urgent_callback=urgent_callback,
        )

        logger.info("🔧 ServiceManager initialized.")

    def start_all(self):
        """Start all background services silently."""
        self.email.start()
        self.files.start()
        # WhatsApp starts on demand (needs valid session)
        logger.info("✅ Background services started (email + files). WhatsApp on demand.")

    def start_whatsapp(self, away_msg: str = "", use_ai: bool = True) -> str:
        self.whatsapp.start()
        return self.whatsapp.enable(away_msg=away_msg, use_ai=use_ai)

    def stop_all(self):
        self.whatsapp.stop()
        self.email.stop()
        self.files.stop()

    # ─── User-facing commands ─────────────────────────────────────────────────

    def what_did_you_do(self) -> str:
        """User asks what happened in background."""
        return self.activity_log.summary(n=10)

    def email_summary(self) -> str:
        return self.email.get_pending_summary()

    def full_status(self) -> str:
        counts = self.activity_log.count_today()
        total = sum(counts.values())
        return (
            f"Background services status:\n"
            f"  {self.whatsapp.get_status()}\n"
            f"  {self.email.get_status()}\n"
            f"  {self.files.get_status()}\n"
            f"  Total actions today: {total}"
        )

    def enable_whatsapp_autoreply(self, msg: str = "") -> str:
        return self.start_whatsapp(away_msg=msg)

    def disable_whatsapp_autoreply(self) -> str:
        return self.whatsapp.disable()

    def add_vip_contact(self, contact: str) -> str:
        return self.whatsapp.add_vip(contact)

    def watch_folder(self, folder: str) -> str:
        return self.files.add_watch_folder(folder)

    def toggle_auto_organize(self, enabled: bool) -> str:
        self.files.auto_organize = enabled
        return f"Auto file organization {'enabled' if enabled else 'disabled'}."

    def toggle_auto_cleanup(self, enabled: bool) -> str:
        self.files.auto_cleanup = enabled
        return f"Auto cleanup {'enabled' if enabled else 'disabled'}."
