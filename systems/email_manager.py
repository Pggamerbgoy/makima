"""
systems/email_manager.py

AI Email Manager
─────────────────
  - Read emails (IMAP) — summarizes with AI
  - Write & send emails (SMTP) — AI-drafted from voice description
  - Smart inbox digest: "what important emails did I get today?"
  - Reply drafting: "reply to [sender] saying [intent]"
  - Priority detection: flags important emails

Commands:
  "Check my emails"
  "Read emails from [sender]"
  "Write email to [address] about [topic]"
  "Reply to [sender] saying [message]"
  "Email digest"
  "Any important emails?"

Setup: Set EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER, SMTP_SERVER in .env
Gmail: use App Password (not regular password), IMAP: imap.gmail.com, SMTP: smtp.gmail.com
"""

import os
import imaplib
import smtplib
import email
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger("Makima.Email")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")  # Use App Password for Gmail
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

PRIORITY_KEYWORDS = [
    "urgent", "asap", "immediately", "important", "action required",
    "deadline", "invoice", "payment", "interview", "offer", "job",
]


def _decode_str(s) -> str:
    if isinstance(s, bytes):
        return s.decode("utf-8", errors="replace")
    if s is None:
        return ""
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += part
    return result


class EmailMessage:
    def __init__(self, uid: str, subject: str, sender: str, date: str, body: str, is_read: bool = False):
        self.uid = uid
        self.subject = subject
        self.sender = sender
        self.date = date
        self.body = body
        self.is_read = is_read
        self.is_priority = any(kw in (subject + body).lower() for kw in PRIORITY_KEYWORDS)


class EmailManager:
    """Full email read/write/reply with AI summarization."""

    MAX_BODY_CHARS = 3000  # Truncate long emails before sending to AI

    def __init__(self, ai):
        self.ai = ai
        self._imap: Optional[imaplib.IMAP4_SSL] = None
        self._check()

    def _check(self):
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            logger.info("Email credentials not set. Email manager disabled.")

    def _connect_imap(self) -> bool:
        try:
            self._imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            self._imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            return True
        except Exception as e:
            logger.warning(f"IMAP connection failed: {e}")
            return False

    def _fetch_emails(self, folder: str = "INBOX", limit: int = 10,
                      sender_filter: str = None, unread_only: bool = False) -> List[EmailMessage]:
        if not EMAIL_ADDRESS:
            return []

        if not self._connect_imap():
            return []

        messages = []
        try:
            self._imap.select(folder)
            criterion = "(UNSEEN)" if unread_only else "ALL"
            if sender_filter:
                criterion = f'(FROM "{sender_filter}")'

            _, data = self._imap.search(None, criterion)
            uids = data[0].split()
            uids = uids[-limit:]  # Most recent

            for uid in reversed(uids):
                try:
                    _, msg_data = self._imap.fetch(uid, "(RFC822)")
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)

                    subject = _decode_str(msg.get("Subject", "(No Subject)"))
                    sender = _decode_str(msg.get("From", "Unknown"))
                    date = msg.get("Date", "")
                    body = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            ct = part.get_content_type()
                            if ct == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                    body = body[:self.MAX_BODY_CHARS]
                    messages.append(EmailMessage(
                        uid=uid.decode(), subject=subject, sender=sender,
                        date=date, body=body
                    ))
                except Exception as e:
                    logger.debug(f"Parse email error: {e}")
        finally:
            try:
                self._imap.logout()
            except Exception:
                pass

        return messages

    # ─── Read & Summarize ─────────────────────────────────────────────────────

    def check_inbox(self, unread_only: bool = True) -> str:
        if not EMAIL_ADDRESS:
            return "Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD in .env"

        emails = self._fetch_emails(unread_only=unread_only, limit=5)
        if not emails:
            return "No new emails." if unread_only else "Your inbox is empty."

        priority = [e for e in emails if e.is_priority]
        lines = []
        if priority:
            lines.append(f"⚠️ {len(priority)} PRIORITY email(s)!")

        for e in emails[:5]:
            flag = "⚠️" if e.is_priority else "📧"
            lines.append(f"{flag} From: {e.sender[:30]} | {e.subject[:40]}")

        lines.append(f"\nTotal: {len(emails)} emails. Say 'email digest' for summaries.")
        return "\n".join(lines)

    def email_digest(self) -> str:
        if not EMAIL_ADDRESS:
            return "Email not configured."

        emails = self._fetch_emails(unread_only=True, limit=5)
        if not emails:
            return "No unread emails to digest."

        summaries = []
        for e in emails:
            snippet = e.body[:500]
            summary = self.ai.chat(
                f"Summarize this email in one sentence:\n"
                f"From: {e.sender}\nSubject: {e.subject}\n{snippet}"
            )
            summaries.append(f"• From {e.sender.split('<')[0].strip()}: {summary}")

        return f"Email digest ({len(emails)} emails):\n" + "\n".join(summaries)

    def read_from(self, sender: str) -> str:
        if not EMAIL_ADDRESS:
            return "Email not configured."

        emails = self._fetch_emails(sender_filter=sender, limit=3)
        if not emails:
            return f"No emails found from '{sender}'."

        e = emails[0]
        summary = self.ai.chat(
            f"Summarize this email clearly:\nFrom: {e.sender}\nSubject: {e.subject}\n{e.body[:1000]}"
        )
        return f"Latest from {e.sender}:\nSubject: {e.subject}\n\n{summary}"

    # ─── Write & Send ─────────────────────────────────────────────────────────

    def draft_email(self, to: str, about: str) -> str:
        """Use AI to draft an email, then send it."""
        prompt = (
            f"Write a professional email.\n"
            f"To: {to}\n"
            f"About: {about}\n"
            f"Format: Subject: [subject]\n\n[body]\n\n"
            f"Keep it concise and professional."
        )
        draft = self.ai.chat(prompt)

        # Parse subject and body
        lines = draft.strip().split("\n")
        subject = "Message from Makima"
        body_start = 0
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line[8:].strip()
                body_start = i + 1
                break

        body = "\n".join(lines[body_start:]).strip()
        return self._send(to=to, subject=subject, body=body)

    def reply_to(self, sender_query: str, intent: str) -> str:
        """Draft and send a reply to a recent email."""
        emails = self._fetch_emails(sender_filter=sender_query, limit=1)
        if not emails:
            return f"Couldn't find a recent email from '{sender_query}'."

        e = emails[0]
        prompt = (
            f"Write a brief reply to this email:\n"
            f"Original From: {e.sender}\n"
            f"Original Subject: {e.subject}\n"
            f"Original Body: {e.body[:500]}\n\n"
            f"My reply intent: {intent}\n"
            f"Write only the reply body, professional and concise."
        )
        reply_body = self.ai.chat(prompt)
        to = e.sender
        subject = f"Re: {e.subject}"
        return self._send(to=to, subject=subject, body=reply_body)

    def _send(self, to: str, subject: str, body: str) -> str:
        if not EMAIL_ADDRESS:
            return "Email not configured."
        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, to, msg.as_string())

            logger.info(f"Email sent to {to}: {subject}")
            return f"Email sent to {to}. Subject: {subject}"
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return f"Failed to send email: {e}"
