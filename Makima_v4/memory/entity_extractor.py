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
            
            if not raw_response:
                return []

            # Clean up the output in case the LLM wrapped it in markdown code blocks
            clean_json = raw_response.replace('```json', '').replace('```', '').strip()
            
            # Robust parsing
            try:
                # 1. Direct JSON load
                triples = json.loads(clean_json)
            except json.JSONDecodeError:
                # 2. Regex fallback if JSON is embedded in text
                import re
                match = re.search(r'\[.*\]', clean_json, re.DOTALL)
                if match:
                    try:
                        triples = json.loads(match.group(0))
                    except:
                        return []
                else:
                    return []

            if isinstance(triples, list):
                # Ensure each item has required keys
                valid_triples = []
                for t in triples:
                    if all(k in t for k in ("subject", "predicate", "object")):
                        valid_triples.append(t)
                return valid_triples
            return []
            
        except Exception as e:
            logging.error(f"[KnowledgeGraph Extractor] Failed to extract triples: {e}")
            return []
