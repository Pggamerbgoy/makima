import unittest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.screen_reader import ScreenReader
from core.claude_coder import ClaudeCoder

class TestVisionAndCoder(unittest.TestCase):
    
    def setUp(self):
        # Mock AI for ScreenReader
        self.mock_ai = MagicMock()
        self.mock_ai.chat.return_value = "Mock AI Description"
        
        # Suppress logging
        import logging
        logging.getLogger("Makima.ScreenReader").setLevel(logging.CRITICAL)
        logging.getLogger("Makima.ClaudeCoder").setLevel(logging.CRITICAL)

    # ─── Screen Reader Tests ────────────────────────────────────────────────

    @patch('agents.screen_reader.PYAUTOGUI_AVAILABLE', True)
    @patch('agents.screen_reader.PIL_AVAILABLE', True)
    @patch('pyautogui.screenshot')
    def test_screen_capture(self, mock_screenshot):
        """Test that screen capture calls the underlying library."""
        sr = ScreenReader(self.mock_ai)
        
        # Mock a PIL image
        mock_img = MagicMock()
        mock_screenshot.return_value = mock_img
        
        img = sr.capture()
        self.assertEqual(img, mock_img)
        mock_screenshot.assert_called_once()

    def test_describe_screen_no_deps(self):
        """Test graceful failure when dependencies are missing."""
        with patch('agents.screen_reader.PYAUTOGUI_AVAILABLE', False):
            sr = ScreenReader(self.mock_ai)
            res = sr.describe_screen()
            self.assertIn("can't access", res.lower())

    @patch('agents.screen_reader.ScreenReader.capture')
    def test_describe_screen_gemini_fallback(self, mock_capture):
        """Test fallback to OCR/AI when Gemini Vision is not configured."""
        sr = ScreenReader(self.mock_ai)
        mock_capture.return_value = MagicMock() # Valid image
        
        # Force Gemini to be unavailable
        sr._gemini_model = None
        
        # Mock OCR extraction
        with patch.object(sr, '_extract_text_ocr', return_value="Error: File not found"):
            desc = sr.describe_screen()
            
            # Should call self.ai.chat with the OCR text
            self.mock_ai.chat.assert_called()
            call_args = self.mock_ai.chat.call_args[0][0]
            self.assertIn("Error: File not found", call_args)

    @patch('agents.screen_reader.ScreenReader.capture')
    def test_identify_app(self, mock_capture):
        """Test app identification logic."""
        sr = ScreenReader(self.mock_ai)
        mock_capture.return_value = MagicMock()
        
        # Mock Gemini response
        sr._gemini_model = MagicMock()
        sr._gemini_model.generate_content.return_value.text = "Visual Studio Code"
        
        res = sr.identify_app()
        self.assertEqual(res, "Visual Studio Code")

    # ─── Claude Coder Tests ─────────────────────────────────────────────────

    def test_claude_init_no_key(self):
        """Test initialization without API key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            coder = ClaudeCoder()
            self.assertFalse(coder.available)

    def test_claude_handle_task(self):
        """Test handling a coding task."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-fake-key"}):
            with patch('core.claude_coder.ANTHROPIC_AVAILABLE', True):
                with patch('anthropic.Anthropic') as mock_client_cls:
                    # Setup mock response
                    mock_instance = mock_client_cls.return_value
                    mock_msg = MagicMock()
                    mock_msg.content = [MagicMock(text="def hello(): pass")]
                    mock_msg.usage.input_tokens = 10
                    mock_msg.usage.output_tokens = 10
                    mock_instance.messages.create.return_value = mock_msg
                    
                    coder = ClaudeCoder()
                    self.assertTrue(coder.available)
                    
                    code = coder.handle_code_task("write hello world")
                    self.assertEqual(code, "def hello(): pass")

    def test_claude_complexity_routing(self):
        """Test that complex tasks route to the smarter model."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-fake-key"}):
            with patch('core.claude_coder.ANTHROPIC_AVAILABLE', True):
                with patch('anthropic.Anthropic') as mock_client_cls:
                    coder = ClaudeCoder()
                    
                    # 1. Simple task
                    coder._pick_model("print hello")
                    # Should be default model (haiku)
                    
                    # 2. Complex task
                    complex_task = "design a microservices architecture with async database"
                    model = coder._pick_model(complex_task)
                    self.assertIn("sonnet", model)

    def test_claude_cooldown(self):
        """Test that repeated failures trigger a cooldown."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-fake-key"}):
             with patch('core.claude_coder.ANTHROPIC_AVAILABLE', True):
                with patch('anthropic.Anthropic'):
                    coder = ClaudeCoder()
                    coder._fail_count = 3
                    coder._last_fail_time = 9999999999 # Future
                    
                    res = coder.handle_code_task("try again")
                    self.assertIsNone(res) # Should return None due to cooldown
    
if __name__ == "__main__":
    unittest.main()
