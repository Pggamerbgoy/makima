"""
agents/app_learner.py

Smart App Learning System
─────────────────────────
When you open ANY app, Makima:
  1. Detects which window just became active
  2. Checks if she already knows this app
  3. If not → asks AI for full workflow guide (commands, tips, workflows)
  4. Saves the knowledge permanently to app_knowledge/
  5. Answers your "how do I..." questions using that saved knowledge
  6. Can guide you step-by-step through any workflow

Bonus: watches your actions inside the app and learns from them too.
"""

import os
import re
import json
import time
import logging
import threading
import platform
from typing import Optional

logger = logging.getLogger("Makima.AppLearner")
OS = platform.system()

APP_KNOWLEDGE_DIR = "app_knowledge"

# Apps we already handle natively — don't auto-learn these
NATIVE_APPS = {
    "spotify", "chrome", "firefox", "edge", "explorer",
    "taskmgr", "cmd", "powershell", "terminal",
    "makima", "makima ai assistant", "makima hud",
    "makima settings", "makima command center",
}

# Window titles containing any of these words are always skipped
IGNORE_KEYWORDS = {
    "makima", "start_makima", "antigravity",
}

# ─── Window detection ─────────────────────────────────────────────────────────

def _get_active_window_title() -> Optional[str]:
    try:
        if OS == "Windows":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return None
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value.strip()
        elif OS == "Linux":
            import subprocess
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2
            )
            return result.stdout.strip() or None
        elif OS == "Darwin":
            import subprocess
            script = 'tell application "System Events" to get name of first process whose frontmost is true'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return result.stdout.strip() or None
    except Exception:
        return None


def _extract_app_name(window_title: str) -> str:
    """Extract clean app name from window title like 'main.py - Visual Studio Code'."""
    separators = [" - ", " — ", " | ", " · "]
    for sep in separators:
        parts = window_title.split(sep)
        if len(parts) > 1:
            # Usually app name is the last part
            return parts[-1].strip()
    return window_title.strip()


# ─── Knowledge Store ──────────────────────────────────────────────────────────

class AppKnowledge:
    """Stores and retrieves AI-generated knowledge about a specific app."""

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.path = os.path.join(APP_KNOWLEDGE_DIR, f"{self._safe_name(app_name)}.json")
        self.data: dict = self._load()

    def _safe_name(self, name: str) -> str:
        return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())[:50]

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self, data: dict):
        self.data = data
        os.makedirs(APP_KNOWLEDGE_DIR, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def exists(self) -> bool:
        return bool(self.data)

    def get_overview(self) -> str:
        return self.data.get("overview", "")

    def get_shortcuts(self) -> list[dict]:
        return self.data.get("shortcuts", [])

    def get_workflows(self) -> list[dict]:
        return self.data.get("workflows", [])

    def find_workflow(self, query: str) -> Optional[dict]:
        """Find the most relevant workflow for a query."""
        query_lower = query.lower()
        best = None
        best_score = 0
        for wf in self.get_workflows():
            name = wf.get("name", "").lower()
            keywords = wf.get("keywords", [])
            score = sum(1 for kw in keywords if kw in query_lower)
            if query_lower in name:
                score += 5
            if score > best_score:
                best_score = score
                best = wf
        return best if best_score > 0 else None

    def search(self, query: str) -> str:
        """Search all knowledge for an answer."""
        query_lower = query.lower()
        results = []

        # Check shortcuts
        for sc in self.get_shortcuts():
            if any(kw in sc.get("action", "").lower() for kw in query_lower.split()):
                results.append(f"Shortcut: {sc.get('action')} → {sc.get('keys')}")

        # Check workflow
        wf = self.find_workflow(query)
        if wf:
            steps = wf.get("steps", [])
            results.append(f"Workflow: {wf['name']}")
            results.extend([f"  Step {i+1}: {s}" for i, s in enumerate(steps)])

        if results:
            return "\n".join(results)

        # Fallback to overview
        return self.get_overview()[:400] if self.get_overview() else ""


# ─── AI Knowledge Generator ───────────────────────────────────────────────────

KNOWLEDGE_PROMPT = """You are a software expert. Generate comprehensive usage knowledge for: {app_name}

Respond ONLY with valid JSON in exactly this structure:
{{
  "app_name": "{app_name}",
  "overview": "2-sentence description of what this app does and its main purpose",
  "category": "one of: creative, productivity, development, communication, gaming, utility, browser, media",
  "shortcuts": [
    {{"action": "Save file", "keys": "Ctrl+S", "description": "Saves current file"}},
    {{"action": "Undo", "keys": "Ctrl+Z", "description": "Undoes last action"}}
  ],
  "workflows": [
    {{
      "name": "Create new project",
      "keywords": ["new", "create", "start", "project"],
      "steps": [
        "Step 1: Go to File menu",
        "Step 2: Click New Project",
        "Step 3: Choose template",
        "Step 4: Set project name and location",
        "Step 5: Click Create"
      ]
    }}
  ],
  "tips": ["Tip 1", "Tip 2", "Tip 3"],
  "common_issues": [
    {{"problem": "App crashes on startup", "solution": "Try running as administrator"}}
  ]
}}

Include at least 8 shortcuts and 5 workflows for common tasks. Make it practical and specific."""


class AppLearner:
    """
    Watches for newly opened apps, learns them via AI,
    and provides step-by-step workflow guidance.
    """

    def __init__(self, ai, speak_callback, auto_learn: bool = False):
        self.ai = ai
        self.speak = speak_callback
        self.auto_learn = auto_learn
        self._known_cache: set[str] = set()
        self._current_app: Optional[str] = None
        self._last_window: Optional[str] = None
        self._active_workflow: Optional[dict] = None
        self._workflow_step: int = 0
        self._running = True

        os.makedirs(APP_KNOWLEDGE_DIR, exist_ok=True)
        self._load_existing_knowledge()

        # Only start background watcher if auto_learn is enabled
        if self.auto_learn:
            self._watcher = threading.Thread(target=self._watch_loop, daemon=True)
            self._watcher.start()
            logger.info("👁️ App Learner started (auto mode).")
        else:
            logger.info("👁️ App Learner ready (manual mode — use 'learn this app').")

    def _load_existing_knowledge(self):
        """Pre-load names of apps we already know."""
        if os.path.isdir(APP_KNOWLEDGE_DIR):
            for fname in os.listdir(APP_KNOWLEDGE_DIR):
                if fname.endswith(".json"):
                    self._known_cache.add(fname[:-5])
        logger.info(f"📚 {len(self._known_cache)} apps already in knowledge base.")

    # ─── Background Watcher ───────────────────────────────────────────────────

    def _watch_loop(self):
        """Poll for active window changes every 2 seconds."""
        while self._running:
            try:
                title = _get_active_window_title()
                if title and title != self._last_window:
                    self._last_window = title
                    # Skip Makima's own windows
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in IGNORE_KEYWORDS):
                        logger.debug(f"Ignoring window: {title}")
                        continue
                    app_name = _extract_app_name(title)
                    if app_name and app_name.lower() not in NATIVE_APPS:
                        self._on_app_switched(app_name)
            except Exception as e:
                logger.debug(f"Watcher error: {e}")
            time.sleep(2)

    def _on_app_switched(self, app_name: str):
        """Called when user switches to a new app."""
        if self._current_app == app_name:
            return
        self._current_app = app_name
        safe_name = re.sub(r"[^a-z0-9_]", "_", app_name.lower())

        # Trigger learning in background so it doesn't block
        if safe_name not in self._known_cache:
            t = threading.Thread(
                target=self._learn_app,
                args=(app_name,),
                daemon=True
            )
            t.start()

    # ─── Learning ─────────────────────────────────────────────────────────────

    def _learn_app(self, app_name: str):
        """Ask AI about the app and save the knowledge."""
        logger.info(f"📖 Learning {app_name}...")
        self.speak(f"I see you opened {app_name}. Let me learn how to use it for you.")

        prompt = KNOWLEDGE_PROMPT.format(app_name=app_name)
        raw, _ = self.ai.chat(prompt)   # ai.chat() → (reply, emotion)

        # Strip markdown fences if present
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except Exception:
                    logger.warning(f"Could not parse AI response for {app_name}")
                    self.speak(f"I tried to learn {app_name} but had trouble understanding the guide.")
                    return
            else:
                self.speak(f"Hmm, I couldn't get good information about {app_name} right now.")
                return

        knowledge = AppKnowledge(app_name)
        knowledge.save(data)
        safe_name = re.sub(r"[^a-z0-9_]", "_", app_name.lower())
        self._known_cache.add(safe_name)

        wf_count = len(data.get("workflows", []))
        sc_count = len(data.get("shortcuts", []))
        self.speak(
            f"Done! I've learned {app_name}. "
            f"I now know {wf_count} workflows and {sc_count} shortcuts. "
            f"Ask me anything about it!"
        )
        logger.info(f"✅ Learned {app_name}: {wf_count} workflows, {sc_count} shortcuts.")

    # ─── Guided Workflows ─────────────────────────────────────────────────────

    def start_workflow(self, app_name: str, query: str) -> str:
        """Find and begin a step-by-step workflow guide."""
        knowledge = AppKnowledge(app_name)
        if not knowledge.exists():
            return f"I haven't learned {app_name} yet. Open it and I'll learn it automatically!"

        wf = knowledge.find_workflow(query)
        if not wf:
            return f"I couldn't find a workflow for '{query}' in {app_name}. Try rephrasing."

        self._active_workflow = wf
        self._workflow_step = 0
        steps = wf.get("steps", [])

        return (
            f"Starting workflow: {wf['name']}. {len(steps)} steps total.\n"
            f"Step 1: {steps[0]}\n"
            f"Say 'next step' to continue, or 'stop guide' to exit."
        )

    def next_step(self) -> str:
        """Advance to the next workflow step."""
        if not self._active_workflow:
            return "No active workflow. Ask me to guide you through something first."

        steps = self._active_workflow.get("steps", [])
        self._workflow_step += 1

        if self._workflow_step >= len(steps):
            name = self._active_workflow["name"]
            self._active_workflow = None
            self._workflow_step = 0
            return f"🎉 Workflow complete! You've finished: {name}"

        step_text = steps[self._workflow_step]
        remaining = len(steps) - self._workflow_step - 1
        suffix = f" ({remaining} step{'s' if remaining != 1 else ''} remaining)" if remaining > 0 else " (last step!)"
        return f"Step {self._workflow_step + 1}: {step_text}{suffix}"

    def stop_workflow(self) -> str:
        self._active_workflow = None
        self._workflow_step = 0
        return "Workflow stopped. Let me know if you need more help!"

    def repeat_step(self) -> str:
        if not self._active_workflow:
            return "No active workflow."
        steps = self._active_workflow.get("steps", [])
        return f"Repeating step {self._workflow_step + 1}: {steps[self._workflow_step]}"

    # ─── Q&A ──────────────────────────────────────────────────────────────────

    def answer_app_question(self, app_name: str, question: str) -> str:
        """Answer a question about an app using saved knowledge."""
        knowledge = AppKnowledge(app_name)
        if not knowledge.exists():
            return f"I haven't learned {app_name} yet. Open it and I'll learn it for you!"

        answer = knowledge.search(question)
        if answer:
            return answer

        # Fallback: ask AI with context
        overview = knowledge.get_overview()
        shortcuts = knowledge.get_shortcuts()[:5]
        context = f"App: {app_name}\nOverview: {overview}\nKey shortcuts: {shortcuts}"
        reply, _ = self.ai.chat(f"Based on this knowledge about {app_name}: {context}\n\nQuestion: {question}")
        return reply

    def get_app_overview(self, app_name: str) -> str:
        knowledge = AppKnowledge(app_name)
        if not knowledge.exists():
            return f"I haven't learned {app_name} yet."
        data = knowledge.data
        overview = data.get("overview", "No overview available.")
        tips = data.get("tips", [])[:3]
        tip_text = "\nTips: " + " | ".join(tips) if tips else ""
        return f"{app_name}: {overview}{tip_text}"

    def list_known_apps(self) -> str:
        if not self._known_cache:
            return "I haven't learned any apps yet. Just open one!"
        names = [n.replace("_", " ").title() for n in self._known_cache]
        return f"I know {len(names)} apps: " + ", ".join(names[:15])

    def learn_current_app(self) -> str:
        """Detect the currently active window and learn it."""
        title = _get_active_window_title()
        if not title:
            return "I can't detect the active window right now."
        app_name = _extract_app_name(title)
        if not app_name:
            return "Couldn't identify the app from the window title."
        safe = re.sub(r"[^a-z0-9_]", "_", app_name.lower())
        if safe in self._known_cache:
            return f"I already know {app_name}! Ask me anything about it."
        return self.force_learn(app_name)

    def force_learn(self, app_name: str) -> str:
        """Manually trigger learning for any app by name."""
        t = threading.Thread(target=self._learn_app, args=(app_name,), daemon=True)
        t.start()
        return f"Learning {app_name} now. I'll tell you when I'm done."
