"""
agents/face_recognition_system.py

Face Recognition System
───────────────────────
Makima knows WHO is talking:
  - Detects faces via webcam on startup
  - Recognizes registered users
  - Greets them by name
  - Loads their personal preferences/memory profile
  - Supports registering new faces via voice command

Dependencies: face_recognition, opencv-python, numpy
Install: pip install face_recognition opencv-python numpy
         (face_recognition also needs cmake + dlib)
"""

import os
import json
import time
import logging
import threading
import pickle
from typing import Optional

logger = logging.getLogger("Makima.FaceRecog")

FACES_DIR = "face_data"
PROFILES_FILE = os.path.join(FACES_DIR, "profiles.json")
ENCODINGS_FILE = os.path.join(FACES_DIR, "encodings.pkl")

try:
    import face_recognition
    import cv2
    import numpy as np
    FR_AVAILABLE = True
except ImportError:
    FR_AVAILABLE = False
    logger.warning("face_recognition / opencv not installed. Face recognition disabled.")
    logger.warning("Install: pip install face_recognition opencv-python numpy")


class UserProfile:
    """Per-user preferences and memory."""

    def __init__(self, name: str, data: dict = None):
        self.name = name
        self.data = data or {
            "name": name,
            "greeting": f"Welcome back, {name}!",
            "preferences": {},
            "interaction_count": 0,
            "last_seen": None,
        }

    def seen(self):
        self.data["interaction_count"] += 1
        self.data["last_seen"] = time.strftime("%Y-%m-%d %H:%M")

    def get_greeting(self) -> str:
        count = self.data["interaction_count"]
        name = self.name
        hour = time.localtime().tm_hour
        time_greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        if count == 0:
            return f"Nice to meet you, {name}! I'm Makima."
        elif count < 5:
            return f"{time_greeting}, {name}!"
        else:
            return f"Hey {name}, good to see you again!"


class FaceRecognitionSystem:
    """
    Webcam-based face recognition with per-user profiles.
    Runs continuously in background, notifies on identity change.
    """

    RECOGNITION_THRESHOLD = 0.5  # Lower = stricter matching
    SCAN_INTERVAL = 3             # Seconds between face scans
    CONFIRM_FRAMES = 2            # Must see same face N times to confirm

    def __init__(self, speak_callback, on_user_change=None):
        self.speak = speak_callback
        self.on_user_change = on_user_change  # called with UserProfile when identity changes

        self.current_user: Optional[UserProfile] = None
        self._profiles: dict[str, dict] = {}
        self._encodings: dict[str, list] = {}  # name → list of face encodings
        self._running = False
        self._cap = None
        self._pending_name: Optional[str] = None  # name being registered
        self._confirm_counter: dict[str, int] = {}

        os.makedirs(FACES_DIR, exist_ok=True)
        self._load_data()

    # ─── Persistence ──────────────────────────────────────────────────────────

    def _load_data(self):
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE) as f:
                    self._profiles = json.load(f)
            except Exception:
                pass

        if os.path.exists(ENCODINGS_FILE):
            try:
                with open(ENCODINGS_FILE, "rb") as f:
                    self._encodings = pickle.load(f)
                logger.info(f"👤 Loaded face data for: {', '.join(self._encodings.keys())}")
            except Exception:
                pass

    def _save_data(self):
        with open(PROFILES_FILE, "w") as f:
            json.dump(self._profiles, f, indent=2)
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(self._encodings, f)

    # ─── Registration ─────────────────────────────────────────────────────────

    def start_registration(self, name: str) -> str:
        """Begin registering a new face."""
        if not FR_AVAILABLE:
            return "Face recognition library not installed."
        self._pending_name = name
        return (
            f"Okay, I'll learn your face, {name}. "
            f"Please look at the camera. "
            f"Say 'done registering' when ready, or I'll auto-capture in 5 seconds."
        )

    def capture_face(self, name: str) -> str:
        """Capture current webcam frame as a face encoding."""
        if not FR_AVAILABLE:
            return "Face recognition not available."
        try:
            cap = cv2.VideoCapture(0)
            time.sleep(0.5)  # Warmup
            ret, frame = cap.read()
            cap.release()

            if not ret:
                return "Couldn't access webcam."

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, locations)

            if not encodings:
                return "No face detected. Please look directly at the camera."

            # Save encoding
            if name not in self._encodings:
                self._encodings[name] = []
            self._encodings[name].append(encodings[0].tolist())

            # Save profile
            if name not in self._profiles:
                self._profiles[name] = UserProfile(name).data
            self._profiles[name]["interaction_count"] = 0

            self._save_data()
            self._pending_name = None
            return f"Got it! I'll recognize you from now on, {name}."

        except Exception as e:
            logger.error(f"Face capture error: {e}")
            return f"Face capture failed: {e}"

    # ─── Recognition ──────────────────────────────────────────────────────────

    def _identify_frame(self, frame) -> Optional[str]:
        """Identify the face in a frame. Returns name or None."""
        if not self._encodings:
            return None
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Use smaller frame for speed
            small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5)
            locations = face_recognition.face_locations(small, model="hog")
            if not locations:
                return None
            locations_full = [(t*2, r*2, b*2, l*2) for t, r, b, l in locations]
            unknown_enc = face_recognition.face_encodings(rgb, locations_full)
            if not unknown_enc:
                return None

            for name, stored_encs in self._encodings.items():
                known = [np.array(e) for e in stored_encs]
                distances = face_recognition.face_distance(known, unknown_enc[0])
                if len(distances) > 0 and min(distances) < self.RECOGNITION_THRESHOLD:
                    return name
            return "Unknown"
        except Exception as e:
            logger.debug(f"Frame identify error: {e}")
            return None

    def _recognition_loop(self):
        """Background loop scanning webcam for faces."""
        if not FR_AVAILABLE:
            return

        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            logger.warning("Webcam not accessible. Face recognition disabled.")
            return

        logger.info("👁️ Face recognition loop started.")

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(1)
                continue

            # Registration mode
            if self._pending_name:
                self.capture_face(self._pending_name)
                time.sleep(0.5)
                continue

            name = self._identify_frame(frame)
            if name:
                # Confirm with multiple frames
                self._confirm_counter[name] = self._confirm_counter.get(name, 0) + 1
                if self._confirm_counter[name] >= self.CONFIRM_FRAMES:
                    self._confirm_counter = {}  # Reset
                    if not self.current_user or self.current_user.name != name:
                        self._switch_user(name)

            time.sleep(self.SCAN_INTERVAL)

        if self._cap:
            self._cap.release()

    def _switch_user(self, name: str):
        """Handle user identity switch."""
        profile_data = self._profiles.get(name, {})
        profile = UserProfile(name, profile_data)
        profile.seen()
        self._profiles[name] = profile.data
        self._save_data()

        self.current_user = profile
        greeting = profile.get_greeting()
        self.speak(greeting)
        logger.info(f"👤 User identified: {name}")

        if self.on_user_change:
            self.on_user_change(profile)

    # ─── Control ──────────────────────────────────────────────────────────────

    def start(self):
        if not FR_AVAILABLE:
            logger.warning("Face recognition unavailable.")
            return
        self._running = True
        t = threading.Thread(target=self._recognition_loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def who_is_there(self) -> str:
        if self.current_user:
            return f"I can see {self.current_user.name} right now."
        return "I don't recognize anyone in front of the camera right now."

    def list_known_faces(self) -> str:
        if not self._encodings:
            return "I don't know any faces yet. Say 'register my face' to teach me yours."
        names = list(self._encodings.keys())
        return f"I know {len(names)} people: " + ", ".join(names)

    def forget_user(self, name: str) -> str:
        if name in self._encodings:
            del self._encodings[name]
        if name in self._profiles:
            del self._profiles[name]
        self._save_data()
        return f"I've forgotten {name}'s face."
