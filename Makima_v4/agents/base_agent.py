"""
Base Agent Class - Foundation for all specialized agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time
from datetime import datetime


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the swarm
    """
    def __init__(self, name: str, ai_handler):
        self.name = name
        self.ai_handler = ai_handler
        self.capabilities = []
        self.performance_stats = {
            'tasks_completed': 0,
            'success_rate': 0.0,
            'avg_response_time': 0.0
        }
    
    @abstractmethod
    def can_handle(self, task: Dict[str, Any]) -> bool:
        """
        Determine if this agent can handle the task
        """
        pass
    
    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the task and return result
        """
        pass
    
    def get_system_prompt(self) -> str:
        """
        Get specialized system prompt for this agent
        """
        return f"You are {self.name}, a specialized AI agent."
    
    def track_performance(self, start_time: float, success: bool):
        """
        Track agent performance metrics
        """
        execution_time = time.time() - start_time
        
        self.performance_stats['tasks_completed'] += 1
        
        # Update success rate
        total = self.performance_stats['tasks_completed']
        current_success = self.performance_stats['success_rate'] * (total - 1)
        self.performance_stats['success_rate'] = (current_success + (1 if success else 0)) / total
        
        # Update avg response time
        current_avg = self.performance_stats['avg_response_time'] * (total - 1)
        self.performance_stats['avg_response_time'] = (current_avg + execution_time) / total
    
    def log(self, message: str, level: str = "INFO"):
        """
        Log agent activities
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.name}] [{level}] {message}")


class AgentTask:
    """
    Standardized task format for agents
    """
    def __init__(self, task_type: str, description: str, context: Dict = None, priority: int = 1):
        self.id = f"task_{int(time.time() * 1000)}"
        self.task_type = task_type
        self.description = description
        self.context = context or {}
        self.priority = priority
        self.created_at = datetime.now()
        self.status = "pending"
        self.result = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.task_type,
            'description': self.description,
            'context': self.context,
            'priority': self.priority,
            'status': self.status
        }


class AgentResult:
    """
    Standardized result format from agents
    """
    def __init__(self, success: bool, data: Any = None, error: str = None, metadata: Dict = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }
