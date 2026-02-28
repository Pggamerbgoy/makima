"""
Research Agent - Web search and information gathering
"""
from Makima_v4.agents.base_agent import BaseAgent, AgentResult
from typing import Dict, Any
import time


class ResearchAgent(BaseAgent):
    """
    Specialized in web research and information gathering
    """
    def __init__(self, ai_handler, web_search_tool=None):
        super().__init__("Research Agent", ai_handler)
        self.capabilities = ['web_search', 'fact_checking', 'summarization']
        self.web_search = web_search_tool  # Your existing web search integration
    
    def can_handle(self, task: Dict[str, Any]) -> bool:
        """
        Can handle research, search, and information tasks
        """
        keywords = ['search', 'find', 'research', 'look up', 'what is', 'who is', 'information about']
        description = task.get('description', '').lower()
        
        return any(keyword in description for keyword in keywords)
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform web research
        """
        start_time = time.time()
        
        try:
            query = task.get('description', '')
            self.log(f"Researching: {query}")
            
            # Use web search if available
            if self.web_search:
                search_results = self.web_search.search(query)
                
                # Summarize findings
                summary = self.summarize_research(search_results, query)
                
                self.track_performance(start_time, True)
                return AgentResult(
                    success=True,
                    data=summary,
                    metadata={'sources': len(search_results)}
                ).to_dict()
            else:
                # Fallback to AI knowledge
                response = self.ai_handler.generate_response(
                    system_prompt=self.get_system_prompt(),
                    user_message=f"Research and provide information about: {query}",
                    temperature=0.3
                )
                
                self.track_performance(start_time, True)
                return AgentResult(success=True, data=response).to_dict()
                
        except Exception as e:
            self.log(f"Research failed: {e}", "ERROR")
            self.track_performance(start_time, False)
            return AgentResult(success=False, error=str(e)).to_dict()
    
    def summarize_research(self, search_results: list, query: str) -> str:
        """
        Summarize web search results
        """
        # Format results
        formatted_results = "\n\n".join([
            f"Source {i+1}: {result.get('title', 'Untitled')}\n{result.get('snippet', '')}"
            for i, result in enumerate(search_results[:5])
        ])
        
        prompt = f"""
        Based on these search results about "{query}", provide a concise summary:
        
        {formatted_results}
        
        Focus on answering the query directly.
        """
        
        summary = self.ai_handler.generate_response(
            system_prompt=self.get_system_prompt(),
            user_message=prompt,
            temperature=0.3
        )
        
        return summary
    
    def get_system_prompt(self) -> str:
        return """
        You are the Research Agent, specialized in finding and synthesizing information.
        Your role is to:
        - Search for accurate, up-to-date information
        - Verify facts from multiple sources
        - Provide clear, concise summaries
        - Cite sources when relevant
        
        Be thorough but concise. Focus on accuracy.
        """
