"""
Executor Agent - System tasks and file operations
"""
from Makima_v4.agents.base_agent import BaseAgent, AgentResult
from typing import Dict, Any
import time
import os
import shutil


class ExecutorAgent(BaseAgent):
    """
    Specialized in file operations and system tasks
    """
    def __init__(self, ai_handler, file_manager=None):
        super().__init__("Executor Agent", ai_handler)
        self.capabilities = ['file_operations', 'system_tasks', 'automation']
        self.file_manager = file_manager  # Your existing file manager
    
    def can_handle(self, task: Dict[str, Any]) -> bool:
        """
        Can handle file and system tasks
        """
        keywords = ['file', 'folder', 'save', 'create', 'delete', 'move', 'copy', 'run', 'execute']
        description = task.get('description', '').lower()
        
        return any(keyword in description for keyword in keywords)
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute system task
        """
        start_time = time.time()
        
        try:
            description = task.get('description', '')
            context = task.get('context', {})
            
            self.log(f"Executor task: {description}")
            
            # Determine operation type
            if 'save' in description.lower() or 'create file' in description.lower():
                result = self.save_file(context)
            elif 'delete' in description.lower():
                result = self.delete_file(context)
            elif 'move' in description.lower():
                result = self.move_file(context)
            else:
                result = self.generic_execution(description, context)
            
            self.track_performance(start_time, True)
            return AgentResult(success=True, data=result).to_dict()
            
        except Exception as e:
            self.log(f"Execution failed: {e}", "ERROR")
            self.track_performance(start_time, False)
            return AgentResult(success=False, error=str(e)).to_dict()
    
    def save_file(self, context: Dict) -> str:
        """
        Save file to disk
        """
        content = context.get('content', '')
        filepath = context.get('filepath', 'output.txt')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"File saved successfully: {filepath}"
        except Exception as e:
            raise Exception(f"Failed to save file: {e}")
    
    def delete_file(self, context: Dict) -> str:
        """
        Delete file
        """
        filepath = context.get('filepath', '')
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return f"File deleted: {filepath}"
        else:
            return f"File not found: {filepath}"
    
    def move_file(self, context: Dict) -> str:
        """
        Move file
        """
        source = context.get('source', '')
        destination = context.get('destination', '')
        
        if os.path.exists(source):
            shutil.move(source, destination)
            return f"File moved: {source} → {destination}"
        else:
            return f"Source file not found: {source}"
    
    def generic_execution(self, description: str, context: Dict) -> str:
        """
        Handle generic execution tasks
        """
        # Use AI to determine what to do
        prompt = f"""
        Execute this task: {description}
        
        Context: {context}
        
        Explain what you would do (I'll implement the actual execution).
        """
        
        response = self.ai_handler.generate_response(
            system_prompt=self.get_system_prompt(),
            user_message=prompt,
            temperature=0.3
        )
        
        return response
    
    def get_system_prompt(self) -> str:
        return """
        You are the Executor Agent, responsible for system operations.
        Your role is to:
        - Perform file operations safely
        - Execute system tasks
        - Automate workflows
        - Ensure data integrity
        
        Always validate operations before execution.
        """
