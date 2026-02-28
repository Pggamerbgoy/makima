"""
Entity Extractor - Uses LLM to extract Graph nodes/edges from text
"""
import json
import logging

class EntityExtractor:
    def __init__(self, ai_handler):
        self.ai = ai_handler

    def extract_from_interaction(self, user_text: str, ai_text: str) -> list:
        """
        Takes raw chat text and asks the LLM to strip it down to facts/triples.
        """
        sys_prompt = """
        You are a Graph Database Entity Extractor.
        Analyze the conversation and extract permanent facts or relationships.
        Output ONLY a pure JSON array containing dictionaries with keys: "subject", "predicate", "object".
        Keep it extremely concise. Ignore conversational filler and polite greetings.
        
        Example conversation:
        User: "I am writing a script in python right now."
        Output:
        [
            {"subject": "user", "predicate": "is coding in", "object": "python"}
        ]
        
        If no facts or concrete relationships are present, output an empty array [].
        """

        convo_prompt = f"User: {user_text}\nAI: {ai_text}"
        
        try:
            # We bypass the history so this doesn't pollute ongoing conversation.
            raw_response = self.ai.generate_response(
                system_prompt=sys_prompt, 
                user_message=convo_prompt, 
                temperature=0.1
            )
            
            # Clean up the output in case the LLM wrapped it in markdown code blocks
            clean_json = raw_response.replace('```json', '').replace('```', '').strip()
            
            if not clean_json:
                return []

            # Parse it
            triples = json.loads(clean_json)
            if isinstance(triples, list):
                return triples
            return []
            
        except Exception as e:
            logging.error(f"[KnowledgeGraph Extractor] Failed to extract triples: {e}")
            return []
