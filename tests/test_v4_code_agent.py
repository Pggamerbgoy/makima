import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from Makima_v4.agents.code_agent import CodeAgent
except ImportError:
    # Fallback if Makima_v4 is not a package yet
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Makima_v4')))
    from agents.code_agent import CodeAgent

class TestV4CodeAgent(unittest.TestCase):
    
    def setUp(self):
        self.mock_ai = MagicMock()
        self.agent = CodeAgent(self.mock_ai)

    def test_capabilities(self):
        """Ensure agent declares correct capabilities."""
        self.assertIn('coding', self.agent.capabilities)
        self.assertIn('debugging', self.agent.capabilities)

    def test_can_handle(self):
        """Test task routing logic."""
        task_yes = {'description': 'write a python script to sort a list'}
        task_no = {'description': 'bake a cake'}
        
        self.assertTrue(self.agent.can_handle(task_yes))
        self.assertFalse(self.agent.can_handle(task_no))

    def test_generate_code_flow(self):
        """Test the code generation workflow."""
        # Mock AI response
        self.mock_ai.generate_response.return_value = "print('Hello World')"
        
        # Mock test_python_code to succeed immediately
        with patch.object(self.agent, 'test_python_code') as mock_test:
            mock_test.return_value = {'success': True, 'output': 'Hello World'}
            
            code = self.agent.generate_code("print hello", {'language': 'python'})
            
            self.assertEqual(code, "print('Hello World')")
            mock_test.assert_called_once()

    def test_fix_code_flow(self):
        """Test that the agent attempts to fix code if testing fails."""
        # First response (bad code), Second response (fixed code)
        self.mock_ai.generate_response.side_effect = ["bad_code", "fixed_code"]
        
        with patch.object(self.agent, 'test_python_code') as mock_test:
            # First test fails, second test (not called in this flow but implied)
            mock_test.return_value = {'success': False, 'error': 'SyntaxError'}
            
            # We mock fix_code to avoid the second AI call complexity in this specific unit test
            with patch.object(self.agent, 'fix_code', return_value="fixed_code") as mock_fix:
                code = self.agent.generate_code("do something", {'language': 'python'})
                
                mock_fix.assert_called()
                self.assertEqual(code, "fixed_code")

    def test_analyze_code(self):
        """Test code analysis fallback to AI."""
        self.mock_ai.generate_response.return_value = "Code looks good."
        result = self.agent.analyze_code("def foo(): pass")
        self.assertEqual(result, "Code looks good.")

    def test_execute_wrapper(self):
        """Test the main execute entry point."""
        with patch.object(self.agent, 'generate_code', return_value="print('ok')"):
            result = self.agent.execute({'description': 'write code', 'context': {}})
            self.assertTrue(result['success'])
            self.assertEqual(result['data'], "print('ok')")

if __name__ == '__main__':
    unittest.main()