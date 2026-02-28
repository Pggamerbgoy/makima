"""
TOOL REGISTRY — Master Integration File
──────────────────────────────────────────────
Single place to initialize ALL tools and
plug them into Makima's existing systems.

Add this to makima_assistant.py __init__:
    from tools.tool_registry import ToolRegistry
    self.tools = ToolRegistry(self)
    self.tools.initialize_all()

Then use anywhere:
    self.tools.cache          → ResponseCache
    self.tools.compressor     → ContextCompressor
    self.tools.finder         → SmartFileFinder
    self.tools.intent         → IntentDetector
    self.tools.proactive      → ProactiveEngine
    self.tools.shortcuts      → ShortcutExpander
"""

from makima_tools.response_cache import ResponseCache
from makima_tools.context_compressor import ContextCompressor
from makima_tools.smart_file_finder import SmartFileFinder
from makima_tools.intent_detector import IntentDetector
from makima_tools.proactive_engine import ProactiveEngine
from makima_tools.shortcut_expander import ShortcutExpander


class ToolRegistry:

    def __init__(self, makima_instance=None):
        self.makima = makima_instance
        self.cache = None
        self.compressor = None
        self.finder = None
        self.intent = None
        self.proactive = None
        self.shortcuts = None

    def initialize_all(self):
        """Initialize every tool. Call once on startup."""
        print("🔧 Initializing Makima tools...")

        # 1. Response Cache — speed up repeated queries
        self.cache = ResponseCache()
        print("  ✅ Response Cache ready")

        # 2. Context Compressor — never lose memory
        ai = getattr(self.makima, 'ai_handler', None) or getattr(self.makima, 'ai', None)
        self.compressor = ContextCompressor(ai_handler=ai)
        print("  ✅ Context Compressor ready")

        # 3. Smart File Finder — fast file search (indexes in background)
        self.finder = SmartFileFinder()
        print("  ✅ Smart File Finder ready (indexing in background)")

        # 4. Intent Detector — understand commands instantly
        self.intent = IntentDetector()
        print("  ✅ Intent Detector ready")

        # 5. Proactive Engine — context-aware suggestions
        speak_fn = getattr(self.makima, 'speak', None)
        execute_fn = getattr(self.makima, 'execute_command', None)
        self.proactive = ProactiveEngine(speak_fn=speak_fn, execute_fn=execute_fn)
        self.proactive.start()
        print("  ✅ Proactive Engine started")

        # 6. Shortcut Expander — personal command shortcuts
        self.shortcuts = ShortcutExpander()
        self.shortcuts.load_defaults()
        print("  ✅ Shortcut Expander ready")

        print("🔧 All tools initialized!\n")
    def process_command(self, raw_input: str) -> tuple[bool, str]:
        """
        Run raw user input through all tools before routing.
        Returns: (is_cached, cleaned_or_expanded_command_or_cached_response)
        """
        # Step 1: Check cache first
        cached = self.cache.get(raw_input)
        if cached:
            return True, cached  # Return immediately, flag as cached

        # Step 2: Expand shortcuts
        expanded = self.shortcuts.expand(raw_input)

        # Step 3: Record usage for auto-shortcut learning
        self.shortcuts.record_usage(expanded)

        # Step 4: Detect intent (attach to context for routing)
        intent = self.intent.detect(expanded)
        print(f"[Tools] {intent}")

        # Step 5: Update proactive engine with latest context
        self.proactive.update_context(last_activity_time=__import__('time').time())

        return False, expanded

    def wrap_response(self, query: str, response: str) -> str:
        """
        Call this after getting a response from the AI.
        Caches it and returns the response unchanged.
        """
        # Don't cache very short responses or errors
        if len(response) > 20 and "error" not in response.lower()[:50]:
            self.cache.store(query, response)
        return response

    def get_stats(self) -> dict:
        """Get stats from all tools."""
        return {
            "cache": self.cache.stats() if self.cache else {},
            "file_index": self.finder.stats() if self.finder else {},
            "shortcuts": len(self.shortcuts.shortcuts) if self.shortcuts else 0
        }
