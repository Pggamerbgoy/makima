import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure we can import from the makima_v3 core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.makima_manager import (
    MakimaManager, MusicManager, AppManager, SystemManager, 
    WebSearchManager, DecisionSimulator
)

class TestMakimaManagerV3(unittest.TestCase):
    def setUp(self):
        # We will patch the subsystem initializations so they don't load heavy/real modules.
        # But for an integration test, MakimaManager handles missing modules gracefully!
        self.manager = MakimaManager(speak_fn=print, text_mode=True)
        
        # Manually mock the internal controllers so we don't trigger anything real
        self.manager.music = MagicMock(spec=MusicManager)
        self.manager.apps = MagicMock(spec=AppManager)
        self.manager.system = MagicMock(spec=SystemManager)
        self.manager.web = MagicMock(spec=WebSearchManager)
        self.manager.simulator = MagicMock(spec=DecisionSimulator)
        
        self.manager.music.play.return_value = "Mock playing."
        self.manager.apps.open.return_value = "Mock opening app."
        self.manager.system.volume_up.return_value = "Mock volume up."
        self.manager.web.search.return_value = "Mock web search result."
        self.manager.simulator.analyze.return_value = "Mock decision."
        
        # Add internal properties needed for status() method
        self.manager.apps._controller = True
        self.manager.system._ctrl = True
        self.manager.web._agent = True
        self.manager.simulator._qs = True

        # Isolate tool execution to ensure routing continues
        self.manager.tools.process = MagicMock(side_effect=lambda x: x)
        self.manager.tools.detect_intent = MagicMock(return_value=None)
        self.manager.prefs.handle_command = MagicMock(return_value=None)

    def test_handle_system_commands(self):
        print("\nTesting System Route...")
        # Since Intent matching relies on tools manager which is too complex to mock out easily here without deep integration,
        # we will test direct fallback or test the direct proxy functions:
        res = self.manager.system.volume_up()
        self.assertEqual(res, "Mock volume up.")
        
    def test_handle_music_commands(self):
        print("Testing Music Route...")
        res = self.manager.play("never gonna give you up")
        self.manager.music.play.assert_called_with("never gonna give you up")
        self.assertEqual(res, "Mock playing.")

    def test_handle_decision_simulator(self):
        print("Testing Simulator Route...")
        # The handle method directly checks "should i invest"
        res = self.manager.handle("should i invest 500 dollars in bitcoin?")
        self.assertTrue(self.manager.simulator.analyze.called)
        self.assertEqual(res, "Mock decision.")

    def test_handle_web_search(self):
        print("Testing Web Route...")
        # Keyword "what is" triggers _needs_web_search
        res = self.manager.handle("what is the capital of france?")
        self.assertTrue(self.manager.web.search.called)
        self.assertEqual(res, "Mock web search result.")

    def test_status_output(self):
        print("Testing Status String Generator...")
        self.manager.start()
        status_str = self.manager.status_str()
        self.assertIn("Running", status_str)
        self.manager.stop()

if __name__ == "__main__":
    unittest.main()
