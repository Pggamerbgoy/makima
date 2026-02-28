"""
Creative Agent - Writing and content creation
"""
from Makima_v4.agents.base_agent import BaseAgent, AgentResult
from typing import Dict, Any
import time


class CreativeAgent(BaseAgent):
    """
    Specialized in writing, brainstorming, and creative tasks
    """
    def __init__(self, ai_handler):
        super().__init__("Creative Agent", ai_handler)
        self.capabilities = ['writing', 'brainstorming', 'storytelling', 'content_creation']
    
    def can_handle(self, task: Dict[str, Any]) -> bool:
        """
        Can handle creative and writing tasks
        """
        keywords = ['write', 'create', 'brainstorm', 'ideas', 'story', 'article', 'blog', 'content']
        description = task.get('description', '').lower()
        
        return any(keyword in description for keyword in keywords)
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute creative task
        """
        start_time = time.time()
        
        try:
            description = task.get('description', '')
            context = task.get('context', {})
            
            self.log(f"Creative task: {description}")
            
            # Determine creativity level
            temperature = 0.8 if 'creative' in description.lower() else 0.6
            
            # Generate creative content
            content = self.ai_handler.generate_response(
                system_prompt=self.get_system_prompt(),
                user_message=self.craft_creative_prompt(description, context),
                temperature=temperature
            )
            
            self.track_performance(start_time, True)
            return AgentResult(success=True, data=content).to_dict()
            
        except Exception as e:
            self.log(f"Creative task failed: {e}", "ERROR")
            self.track_performance(start_time, False)
            return AgentResult(success=False, error=str(e)).to_dict()
    
    def craft_creative_prompt(self, description: str, context: Dict) -> str:
        """
        Craft an effective creative prompt
        """
        style = context.get('style', 'professional')
        length = context.get('length', 'medium')
        tone = context.get('tone', 'neutral')
        
        prompt = f"""
        Task: {description}
        
        Style: {style}
        Length: {length}
        Tone: {tone}
        
        Create compelling, original content that fulfills this request.
        """
        
        return prompt
    
    def get_system_prompt(self) -> str:
        return """
        You are the Creative Agent, a master of written expression.
        Your role is to:
        - Write engaging, original content
        - Generate creative ideas
        - Craft compelling narratives
        - Adapt style and tone as needed
        
        Be creative, but stay on-topic and purposeful.
        """
