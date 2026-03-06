"""
agents/screen_reader.py

Screen Reader / Vision System
───────────────────────────────
Makima can see your screen and describe it:
  - "What's on my screen?" → describes current screen content
  - "Read this page" → reads and summarizes visible text
  - "What app is open?" → identifies active application
  - "Help me with this" → gives contextual help based on screen
  - "Read this error" → reads and explains error messages
  - "Describe this image" → describes any visible image
  - Screen-aware AI: injects current screen context into all AI prompts

Uses: Gemini Vision API (primary) or pytesseract OCR (fallback for text extraction)
Install: pip install pytesseract pillow
         (also install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki)
"""

import os
import io
import time
import logging
import base64
import threading
import platform
from typing import Optional
from datetime import datetime

logger = logging.getLogger("Makima.ScreenReader")
OS = platform.system()

SCREENSHOTS_DIR = "screenshots"

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    # Auto-detect Tesseract on Windows default paths
    if OS == "Windows":
        _tess_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.getenv("LOCALAPPDATA", ""), r"Tesseract-OCR\tesseract.exe")
        ]
        for _p in _tess_paths:
            if os.path.exists(_p):
                pytesseract.pytesseract.tesseract_cmd = _p
                break
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from google import genai as _genai
    GEMINI_AVAILABLE = True
except (ImportError, TypeError, Exception):
    _genai = None
    GEMINI_AVAILABLE = False


class ScreenReader:
    """
    Captures the screen and uses AI vision to describe, read, and help with content.
    """

    CONTEXT_INTERVAL = 10  # Seconds between auto-context updates

    def __init__(self, ai):
        self.ai = ai
        self._last_screenshot: Optional[object] = None
        self._last_description: str = ""
        self._last_context_time: float = 0
        self._gemini_client = None
        self._gemini_vision_model = "gemini-2.0-flash"
        self._auto_context = False
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        self._init_gemini_vision()

    def _init_gemini_vision(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not GEMINI_AVAILABLE or not api_key:
            return
        try:
            self._gemini_client = _genai.Client(api_key=api_key)
            logger.info("✅ Gemini Vision ready for screen reading.")
        except Exception as e:
            logger.warning(f"Gemini Vision init failed: {e}")

    # ─── Screenshot ───────────────────────────────────────────────────────────

    def capture(self) -> Optional[object]:
        """Capture current screen. Returns PIL Image or None."""
        if not PYAUTOGUI_AVAILABLE or not PIL_AVAILABLE:
            return None
        try:
            screenshot = pyautogui.screenshot()
            self._last_screenshot = screenshot
            return screenshot
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None

    def capture_region(self, x: int, y: int, w: int, h: int) -> Optional[object]:
        """Capture a specific screen region."""
        if not PYAUTOGUI_AVAILABLE or not PIL_AVAILABLE:
            return None
        try:
            return pyautogui.screenshot(region=(x, y, w, h))
        except Exception as e:
            logger.warning(f"Region capture failed: {e}")
            return None

    def _image_to_base64(self, image) -> str:
        """Convert PIL image to base64 string for API calls."""
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    # ─── Vision Analysis ──────────────────────────────────────────────────────

    def _analyze_with_gemini(self, image, prompt: str) -> Optional[str]:
        """Use Gemini Vision to analyze an image."""
        if not self._gemini_client:
            return None
        try:
            # Convert PIL image to bytes for the new genai API
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()

            response = self._gemini_client.models.generate_content(
                model=self._gemini_vision_model,
                contents=[
                    {"role": "user", "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(image_bytes).decode()}},
                    ]}
                ],
            )
            return (response.text or "").strip() or None
        except Exception as e:
            logger.warning(f"Gemini vision error: {e}")
            return None

    def _extract_text_ocr(self, image) -> str:
        """Extract text from image using Tesseract OCR."""
        if not TESSERACT_AVAILABLE:
            return ""
        try:
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR error: {e}")
            return ""

    # ─── Public Commands ──────────────────────────────────────────────────────

    def describe_screen(self) -> str:
        """Capture screen and describe what's visible."""
        image = self.capture()
        if not image:
            return "I can't access the screen right now. Make sure pyautogui is installed."

        # Try Gemini Vision first
        description = self._analyze_with_gemini(
            image,
            "Describe what's currently on this computer screen in 2-3 sentences. "
            "Focus on what the user is doing and what content is visible. Be specific."
        )

        if not description:
            # Fallback: OCR + AI summary
            text = self._extract_text_ocr(image)
            if text:
                description, _ = self.ai.chat(
                    f"Summarize what's on a computer screen based on this extracted text:\n{text[:1000]}"
                )
            else:
                description = "I can see your screen but can't make out the content clearly."

        self._last_description = description
        return description

    def read_screen(self) -> str:
        """Read and return all visible text on screen."""
        image = self.capture()
        if not image:
            return "Screen capture unavailable."

        # Try Gemini for structured text extraction
        text = self._analyze_with_gemini(
            image,
            "Extract and return ALL text visible on this screen, in reading order. "
            "Include headings, buttons, labels, and body text. Format it clearly."
        )

        if not text and TESSERACT_AVAILABLE:
            text = self._extract_text_ocr(image)

        if not text:
            return "No text found on screen, or vision system unavailable."

        return text[:2000]  # Cap output length

    def get_screen_help(self) -> str:
        """Give contextual help based on current screen content."""
        image = self.capture()
        if not image:
            return "Can't see your screen to help."

        help_text = self._analyze_with_gemini(
            image,
            "Look at this computer screen and provide helpful guidance. "
            "What is the user trying to do? What are the best next steps? "
            "If there's an error, explain it and how to fix it. "
            "If it's an unfamiliar application, explain key elements visible. "
            "Be practical and specific."
        )

        if help_text:
            return help_text
        reply, _ = self.ai.chat(
            f"Help me with what I see on screen: {self._last_description}"
        )
        return reply

    def read_error(self) -> str:
        """Find and explain any error message on screen."""
        image = self.capture()
        if not image:
            return "Can't access screen."

        explanation = self._analyze_with_gemini(
            image,
            "Find any error messages, warnings, or issues visible on this screen. "
            "Explain what the error means and provide step-by-step instructions to fix it. "
            "If no error is visible, say so."
        )
        return explanation or "No errors detected on screen."

    def identify_app(self) -> str:
        """Identify what application is currently in focus."""
        image = self.capture()
        if not image:
            return "Can't see screen."

        result = self._analyze_with_gemini(
            image,
            "What application or website is currently open on this screen? "
            "Just name it and describe what the user is looking at in one sentence."
        )
        return result or "Can't identify the current application."

    def compare_before_after(self, before, after) -> str:
        """Compare two screenshots and describe what changed."""
        if not self._gemini_client:
            return "Gemini Vision required for comparison."
        try:
            # Convert both PIL images to base64
            parts = [{"text": "Compare these two screenshots and describe what changed between them."}]
            for img in (before, after):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}})

            response = self._gemini_client.models.generate_content(
                model=self._gemini_vision_model,
                contents=[{"role": "user", "parts": parts}],
            )
            return (response.text or "").strip()
        except Exception as e:
            return f"Comparison failed: {e}"

    # ─── Context for AI ───────────────────────────────────────────────────────

    def get_screen_context(self) -> str:
        """
        Get a brief screen context string to inject into AI prompts.
        Cached for CONTEXT_INTERVAL seconds to avoid constant screenshots.
        """
        now = time.time()
        if now - self._last_context_time < self.CONTEXT_INTERVAL and self._last_description:
            return self._last_description

        image = self.capture()
        if not image:
            return ""

        context = self._analyze_with_gemini(
            image,
            "In one sentence, what is the user currently doing on their computer? "
            "What app is open and what are they looking at?"
        )
        if context:
            self._last_description = context
            self._last_context_time = now
        return self._last_description

    def save_screenshot(self, label: str = "") -> str:
        """Save a labeled screenshot."""
        image = self.capture()
        if not image:
            return "Screenshot failed."
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        label = label.replace(" ", "_")[:20]
        fname = f"{ts}_{label}.png" if label else f"{ts}.png"
        path = os.path.join(SCREENSHOTS_DIR, fname)
        image.save(path)
        return f"Screenshot saved: {path}"
