"""
remote/telegram_remote.py
Control Makima from anywhere via Telegram bot.
Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
Run this as a standalone script alongside the main assistant.
"""

import os
import logging
import threading

logger = logging.getLogger("Makima.Telegram")

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class TelegramRemote:
    """
    Exposes Makima's command router over Telegram.
    Usage: instantiate and call .start() in a background thread.
    """

    def __init__(self, router):
        self.router = router

    def start(self):
        if not TELEGRAM_AVAILABLE:
            logger.warning("python-telegram-bot not installed. Telegram remote disabled.")
            return
        if not BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram remote disabled.")
            return

        app = Application.builder().token(BOT_TOKEN).build()

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Security: only respond to allowed chat
            if ALLOWED_CHAT_ID and str(update.effective_chat.id) != ALLOWED_CHAT_ID:
                await update.message.reply_text("Unauthorized.")
                return
            user_input = update.message.text
            response = self.router.route(user_input)
            await update.message.reply_text(response or "Done.")

        async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text("Makima is online. Send commands.")

        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Telegram bot running.")
        app.run_polling()

    def start_in_thread(self):
        t = threading.Thread(target=self.start, daemon=True)
        t.start()
