"""
Code Agent - Programming expert
"""
from Makima_v4.agents.base_agent import BaseAgent, AgentResult
from typing import Dict, Any
import time
import subprocess
import tempfile
import os


class CodeAgent(BaseAgent):
    """
    Specialized in programming, debugging, and code analysis
    """
    def __init__(self, ai_handler, code_analyzer=None):
        super().__init__("Code Agent", ai_handler)
        self.capabilities = ['coding', 'debugging', 'code_review', 'refactoring']
        self.code_analyzer = code_analyzer  # Semantic analyzer
    
    def can_handle(self, task: Dict[str, Any]) -> bool:
        """
        Can handle coding and programming tasks
        """
        keywords = ['code', 'program', 'script', 'debug', 'fix', 'implement', 'function', 'class']
        description = task.get('description', '').lower()
        
        return any(keyword in description for keyword in keywords)
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute coding task
        """
        start_time = time.time()
        
        try:
            description = task.get('description', '')
            context = task.get('context', {})
            
            self.log(f"Coding task: {description}")
            
            # Determine task type
            if 'debug' in description.lower() or 'fix' in description.lower():
                result = self.debug_code(context.get('code', ''), description)
            elif 'analyze' in description.lower() or 'review' in description.lower():
                result = self.analyze_code(context.get('code', ''))
            else:
                result = self.generate_code(description, context)
            
            self.track_performance(start_time, True)
            return AgentResult(success=True, data=result).to_dict()
            
        except Exception as e:
            self.log(f"Code task failed: {e}", "ERROR")
            self.track_performance(start_time, False)
            return AgentResult(success=False, error=str(e)).to_dict()
    
    def generate_code(self, description: str, context: Dict) -> str:
        """
        Generate new code
        """
        language = context.get('language', 'python')
        
        prompt = f"""
        Write {language} code for: {description}
        
        Requirements:
        - Clean, readable code
        - Include comments
        - Handle errors
        - Follow best practices
        
        Return only the code, no explanations.
        """
        
        code = self.ai_handler.generate_response(
            system_prompt=self.get_system_prompt(),
            user_message=prompt,
            temperature=0.2
        )
        
        # Test the code
        if language.lower() == 'python':
            test_result = self.test_python_code(code)
            if not test_result['success']:
                self.log(f"Generated code failed: {test_result['error']}", "WARNING")
                # Try to fix
                code = self.fix_code(code, test_result['error'])
        
        return code
    
    def debug_code(self, code: str, issue_description: str) -> str:
        """
        Debug existing code
        """
        prompt = f"""
        Debug this code:
        
        ```
        {code}
        ```
        
        Issue: {issue_description}
        
        Provide:
        1. What's wrong
        2. Fixed code
        3. Explanation
        """
        
        response = self.ai_handler.generate_response(
            system_prompt=self.get_system_prompt(),
            user_message=prompt,
            temperature=0.2
        )
        
        return response
    
    def analyze_code(self, code: str) -> str:
        """
        Analyze code quality
        """
        if self.code_analyzer:
            analysis = self.code_analyzer.analyze_code(code)
            return self.format_analysis(analysis)
        
        # Fallback to AI analysis
        prompt = f"""
        Analyze this code:
        
        ```
        {code}
        ```
        
        Check for:
        - Bugs
        - Performance issues
        - Security vulnerabilities
        - Code smells
        - Improvements
        """
        
        analysis = self.ai_handler.generate_response(
            system_prompt=self.get_system_prompt(),
            user_message=prompt,
            temperature=0.3
        )
        
        return analysis
    
    def test_python_code(self, code: str) -> Dict[str, Any]:
        """
        Test Python code execution
        """
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run code
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Clean up
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return {'success': True, 'output': result.stdout}
            else:
                return {'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Code execution timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def fix_code(self, code: str, error: str) -> str:
        """
        Attempt to fix code based on error
        """
        prompt = f"""
        This code has an error:
        
        ```
        {code}
        ```
        
        Error: {error}
        
        Fix the code. Return only the corrected code.
        """
        
        fixed_code = self.ai_handler.generate_response(
            system_prompt=self.get_system_prompt(),
            user_message=prompt,
            temperature=0.1
        )
        
        return fixed_code
    
    def format_analysis(self, analysis: Dict) -> str:
        """
        Format code analysis results
        """
        output = "🔍 CODE ANALYSIS:\n\n"
        
        if 'complexity' in analysis:
            output += "COMPLEXITY:\n"
            for item in analysis['complexity']:
                output += f"  ⚠️ Line {item['line']}: {item['complexity']} - {item['warning']}\n"
            output += "\n"
        
        if 'security' in analysis:
            output += "SECURITY:\n"
            for vuln in analysis['security']:
                output += f"  🚨 Line {vuln['line']}: {vuln['type']} - {vuln['description']}\n"
            output += "\n"
        
        if 'optimizations' in analysis:
            output += "OPTIMIZATIONS:\n"
            for opt in analysis['optimizations']:
                output += f"  💡 Line {opt['line']}: {opt['type']} - {opt['benefit']}\n"
            output += "\n"
        
        return output
    
    def get_system_prompt(self) -> str:
        return """
        You are the Code Agent, a senior software engineer AI.
        Your role is to:
        - Write clean, efficient code
        - Debug and fix issues
        - Analyze code quality
        - Suggest improvements
        - Follow best practices
        
        Always prioritize code quality and security.
        """
