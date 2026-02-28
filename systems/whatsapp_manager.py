"""
systems/whatsapp_manager.py

WhatsApp Manager
─────────────────
  - Auto-reply to messages when you're busy / in focus mode
  - AI-generated contextual replies (not just static "I'm busy")
  - Read latest messages via Selenium + WhatsApp Web
  - Send messages by voice command
  - Set custom away messages per contact

Commands:
  "Enable WhatsApp auto-reply"
  "Disable WhatsApp auto-reply"
  "Set away message to [text]"
  "Read my WhatsApp messages"
  "Send WhatsApp to [contact]: [message]"
  "Who messaged me on WhatsApp?"

Note: Uses WhatsApp Web via Selenium. Requires Chrome + ChromeDriver.
Install: pip install selenium webdriver-manager
"""

import os
import time
import logging
import threading
import json
from typing import Optional, Callable

logger = logging.getLogger("Makima.WhatsApp")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

WHATSAPP_URL = "https://web.whatsapp.com"
SESSION_DIR = "whatsapp_session"
CONTACTS_FILE = "whatsapp_contacts.json"

DEFAULT_AWAY_MESSAGE = (
    "Hi! I'm currently busy and can't respond right now. "
    "Makima (my AI assistant) is handling my messages. I'll get back to you soon!"
)


class WhatsAppManager:
    """
    WhatsApp Web automation for auto-reply, message reading, and sending.
    """

    CHECK_INTERVAL = 30  # Seconds between unread message checks

    def __init__(self, ai, speak_callback: Callable):
        self.ai = ai
        self.speak = speak_callback
        self.auto_reply_enabled = False
        self.away_message = DEFAULT_AWAY_MESSAGE
        self.use_ai_replies = True  # Generate smart replies vs static message
        self._driver: Optional[object] = None
        self._replied_to: set = set()  # Track replied messages to avoid duplicates
        self._contacts: dict = self._load_contacts()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False

    def _load_contacts(self) -> dict:
        if os.path.exists(CONTACTS_FILE):
            try:
                with open(CONTACTS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_contacts(self):
        with open(CONTACTS_FILE, "w") as f:
            json.dump(self._contacts, f, indent=2)

    # ─── Browser Setup ────────────────────────────────────────────────────────

    def _init_browser(self) -> bool:
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not installed. WhatsApp automation disabled.")
            return False
        try:
            options = Options()
            options.add_argument(f"--user-data-dir={os.path.abspath(SESSION_DIR)}")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            # Don't run headless so QR code can be scanned on first run
            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.get(WHATSAPP_URL)
            logger.info("WhatsApp Web opened. Scan QR code if first time.")
            return True
        except Exception as e:
            logger.error(f"Browser init failed: {e}")
            return False

    def _wait_for_load(self, timeout: int = 60) -> bool:
        """Wait for WhatsApp Web to finish loading."""
        try:
            WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]'))
            )
            return True
        except Exception:
            return False

    # ─── Message Reading ──────────────────────────────────────────────────────

    def _get_unread_chats(self) -> list[dict]:
        """Scrape unread message badges from WhatsApp Web."""
        unread = []
        try:
            badges = self._driver.find_elements(By.CSS_SELECTOR, '[data-testid="icon-unread-count"]')
            for badge in badges:
                try:
                    chat_item = badge.find_element(By.XPATH, "./ancestor::div[@data-testid='list-item-v3']")
                    contact_el = chat_item.find_element(By.CSS_SELECTOR, "[data-testid='cell-frame-title'] span")
                    preview_el = chat_item.find_element(By.CSS_SELECTOR, "[data-testid='last-msg-status'] ~ span")
                    unread.append({
                        "contact": contact_el.text,
                        "preview": preview_el.text,
                        "element": chat_item,
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Get unread chats error: {e}")
        return unread

    def _open_chat(self, contact: str):
        """Click on a chat with given contact name."""
        try:
            search = self._driver.find_element(By.CSS_SELECTOR, '[data-testid="chat-list-search"]')
            search.clear()
            search.send_keys(contact)
            time.sleep(1.5)
            result = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="cell-frame-title"]'))
            )
            result.click()
            time.sleep(1)
        except Exception as e:
            logger.debug(f"Open chat error: {e}")

    def _get_last_message(self) -> Optional[str]:
        """Get the text of the last message in the current open chat."""
        try:
            messages = self._driver.find_elements(By.CSS_SELECTOR, '[data-testid="msg-container"]')
            if messages:
                last = messages[-1]
                text_el = last.find_element(By.CSS_SELECTOR, "span.selectable-text")
                return text_el.text
        except Exception:
            pass
        return None

    def _send_message(self, text: str):
        """Type and send a message in the currently open chat."""
        try:
            box = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]'))
            )
            box.click()
            box.send_keys(text)
            box.send_keys(Keys.ENTER)
        except Exception as e:
            logger.debug(f"Send message error: {e}")

    # ─── AI Reply Generation ──────────────────────────────────────────────────

    def _generate_reply(self, contact: str, message: str) -> str:
        if not self.use_ai_replies:
            return self.away_message

        prompt = (
            f"You are Makima, an AI assistant replying on behalf of the user who is currently busy.\n"
            f"Contact '{contact}' sent this message: '{message}'\n"
            f"Write a brief, friendly auto-reply (max 2 sentences) acknowledging their message "
            f"and letting them know the user will respond soon. "
            f"Don't pretend to be human — mention you're an AI assistant if relevant."
        )
        return self.ai.chat(prompt)

    # ─── Auto-Reply Monitor ───────────────────────────────────────────────────

    def _monitor_loop(self):
        if not self._init_browser():
            return
        if not self._wait_for_load():
            self.speak("WhatsApp Web didn't load. Please scan the QR code and try again.")
            return

        logger.info("✅ WhatsApp monitor running.")

        while self._running and self.auto_reply_enabled:
            try:
                unread = self._get_unread_chats()
                for chat in unread:
                    contact = chat["contact"]
                    preview = chat["preview"]
                    msg_id = f"{contact}:{preview[:20]}"

                    if msg_id not in self._replied_to:
                        self._replied_to.add(msg_id)
                        self._open_chat(contact)
                        time.sleep(1)
                        last_msg = self._get_last_message() or preview
                        reply = self._generate_reply(contact, last_msg)
                        self._send_message(reply)
                        logger.info(f"Auto-replied to {contact}: {reply[:60]}...")
                        self.speak(f"Auto-replied to {contact} on WhatsApp.")
            except Exception as e:
                logger.debug(f"Monitor loop error: {e}")
            time.sleep(self.CHECK_INTERVAL)

    # ─── Public Interface ─────────────────────────────────────────────────────

    def enable_auto_reply(self) -> str:
        if self.auto_reply_enabled:
            return "WhatsApp auto-reply is already on."
        self.auto_reply_enabled = True
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        return "WhatsApp auto-reply enabled. I'll respond to messages while you're busy."

    def disable_auto_reply(self) -> str:
        self.auto_reply_enabled = False
        self._running = False
        return "WhatsApp auto-reply disabled."

    def set_away_message(self, message: str) -> str:
        self.away_message = message
        self.use_ai_replies = False
        return f"Away message set to: {message}"

    def set_ai_replies(self, enabled: bool) -> str:
        self.use_ai_replies = enabled
        mode = "AI-generated smart replies" if enabled else "static away message"
        return f"WhatsApp will now use {mode}."

    def send_message(self, contact: str, message: str) -> str:
        if not self._driver:
            if not self._init_browser():
                return "WhatsApp browser not available."
            if not self._wait_for_load(30):
                return "WhatsApp didn't load."
        self._open_chat(contact)
        self._send_message(message)
        return f"Message sent to {contact} on WhatsApp."

    def read_messages(self) -> str:
        if not self._driver:
            return "WhatsApp isn't open. Enable auto-reply first to open WhatsApp Web."
        unread = self._get_unread_chats()
        if not unread:
            return "No unread WhatsApp messages."
        lines = [f"- {c['contact']}: {c['preview']}" for c in unread[:5]]
        return f"You have {len(unread)} unread WhatsApp messages:\n" + "\n".join(lines)
