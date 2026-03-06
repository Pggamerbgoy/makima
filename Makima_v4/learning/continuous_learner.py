"""
Continuous Learner - Main learning system
"""
from Makima_v4.learning.feedback_database import FeedbackDatabase
from Makima_v4.learning.pattern_analyzer import PatternAnalyzer
from typing import Dict, Any
from datetime import datetime
import time
import threading


class ContinuousLearner:
    """
    Learns from every interaction and improves over time
    """
    def __init__(self, preferences_manager=None, knowledge_graph=None, ai_handler=None, on_conflict=None):
        self.on_conflict = on_conflict
        self.feedback_db = FeedbackDatabase()
        self.pattern_analyzer = PatternAnalyzer()
        self.preferences_manager = preferences_manager
        
        self.knowledge_graph = knowledge_graph
        if ai_handler:
            try:
                from Makima_v4.memory.entity_extractor import EntityExtractor
                self.entity_extractor = EntityExtractor(ai_handler)
            except ImportError:
                self.entity_extractor = None
        else:
            self.entity_extractor = None
        
        # Learning settings
        self.learning_enabled = True
        self.auto_learn_interval = 86400  # 24 hours
        self.last_learning_time = 0
        
        # Start background learning
        self.start_background_learning()
        
        print("🧠 Continuous Learning System initialized")
    
    def record_interaction(self, user_input: str, ai_response: str,
                          outcome: str = 'neutral', context: Dict = None,
                          response_time: float = 0.0):
        """
        Record an interaction for learning
        
        Args:
            user_input: User's command
            ai_response: AI's response
            outcome: 'success', 'failure', or 'neutral'
            context: Additional context
            response_time: Response time in seconds
        """
        if not self.learning_enabled:
            return
        
        self.feedback_db.store_interaction(
            user_input=user_input,
            ai_response=ai_response,
            outcome=outcome,
            context=context,
            response_time=response_time
        )
        
        # Asynchronously extract entities into Graph Memory
        if self.entity_extractor and self.knowledge_graph:
            def extract_and_map():
                triples = self.entity_extractor.extract_from_interaction(user_input, ai_response)
                for triple in triples:
                    subj = triple.get("subject")
                    pred = triple.get("predicate")
                    obj = triple.get("object")
                    if subj and pred and obj:
                        conflict = self.knowledge_graph.add_edge(subj, obj, pred)
                        if conflict:
                            print(f"⚖️ [Consistency Guard] Found contradiction for '{subj}':")
                            print(f"   Existing: {conflict['relationship']} -> {conflict['old_object']}")
                            print(f"   New:      {conflict['relationship']} -> {conflict['new_object']}")
                            if self.on_conflict:
                                try:
                                    self.on_conflict(conflict)
                                except Exception as e:
                                    print(f"Error in on_conflict callback: {e}")
                        else:
                            print(f"🧩 [Graph] Mapped: [{subj}] --({pred})--> [{obj}]")
            
            threading.Thread(target=extract_and_map, daemon=True).start()
    
    def record_user_feedback(self, interaction_id: int, satisfaction: int):
        """
        Record explicit user feedback (1-5 stars)
        """
        # Update interaction with satisfaction score
        # This would update the database
        pass
    
    def learn_from_recent_interactions(self, days: int = 7):
        """
        Analyze recent interactions and update preferences
        """
        print(f"🔍 Analyzing last {days} days of interactions...")
        
        # Get recent interactions
        interactions = self.feedback_db.get_recent_interactions(days=days)
        
        if len(interactions) < 10:
            print("Not enough data for learning yet")
            return
        
        # Find patterns
        patterns = self.pattern_analyzer.analyze_interactions(interactions)
        
        print(f"📊 Found {len(patterns)} patterns")
        
        # Update preferences based on patterns
        for pattern in patterns:
            if pattern['confidence'] >= 0.7:
                self.apply_pattern(pattern)
        
        # Store patterns in database
        for pattern in patterns:
            self.feedback_db.store_pattern(
                pattern_type=pattern['type'],
                pattern_data=pattern['data']
            )
        
        print("✅ Learning complete!")
    
    def apply_pattern(self, pattern: Dict):
        """
        Apply a learned pattern to preferences
        """
        key = None
        value = None

        if pattern['type'] == 'time_based':
            key = f"command_at_{pattern['data']['hour']}"
            value = pattern['data']['command']
            self.feedback_db.store_preference(key, value, pattern['confidence'])
            print(f"  Learned: {pattern['pattern']} (confidence: {pattern['confidence']:.2f})")
        
        elif pattern['type'] == 'context_based':
            key = f"command_for_{pattern['data']['context']}"
            value = pattern['data']['command']
            self.feedback_db.store_preference(key, value, pattern['confidence'])
            print(f"  Learned: {pattern['pattern']} (confidence: {pattern['confidence']:.2f})")
        
        elif pattern['type'] == 'response_style':
            key = "preferred_response_style"
            value = pattern['data']['preferred_style']
            self.feedback_db.store_preference(key, value, pattern['confidence'])
            print(f"  Learned: {pattern['pattern']} (confidence: {pattern['confidence']:.2f})")
        
        # Update preferences manager if available
        if self.preferences_manager and key and value:
            try:
                self.preferences_manager.set_preference(key, value)
            except:
                pass
    
    def get_learned_preferences(self) -> Dict[str, Any]:
        """
        Get all learned preferences
        """
        return {
            pref['key']: pref['value']
            for pref in self.feedback_db.get_all_preferences()
            if pref['confidence'] >= 0.6
        }
    
    def predict_next_action(self, context: Dict) -> str:
        """
        Predict what user might want next based on context
        """
        hour = context.get('hour', datetime.now().hour)
        active_app = context.get('active_window', '').lower()
        
        # Check time-based patterns
        time_pref = self.feedback_db.get_preference(f"command_at_{hour}")
        if time_pref and time_pref['confidence'] >= 0.7:
            return time_pref['value']
        
        # Check context-based patterns
        if active_app:
            context_pref = self.feedback_db.get_preference(f"command_for_{active_app}")
            if context_pref and context_pref['confidence'] >= 0.7:
                return context_pref['value']
        
        return None
    
    def get_learning_stats(self) -> Dict:
        """
        Get learning statistics
        """
        return self.feedback_db.get_stats()
    
    def start_background_learning(self):
        """
        Start background thread for periodic learning
        """
        def learning_loop():
            while self.learning_enabled:
                current_time = time.time()
                
                # Learn once per day
                if current_time - self.last_learning_time >= self.auto_learn_interval:
                    try:
                        self.learn_from_recent_interactions(days=7)
                        self.last_learning_time = current_time
                    except Exception as e:
                        print(f"Background learning error: {e}")
                
                # Sleep for 1 hour
                time.sleep(3600)
        
        learning_thread = threading.Thread(target=learning_loop, daemon=True)
        learning_thread.start()
    
    def export_learning_report(self) -> str:
        """
        Generate a human-readable learning report
        """
        stats = self.get_learning_stats()
        preferences = self.feedback_db.get_all_preferences()
        patterns = self.feedback_db.get_patterns()
        
        report = f"""
🧠 MAKIMA LEARNING REPORT
{'=' * 50}

STATISTICS:
  Total Interactions: {stats['total_interactions']}
  Success Rate: {stats['success_rate']}%
  Learned Preferences: {stats['learned_preferences']}
  Discovered Patterns: {stats['discovered_patterns']}

TOP LEARNED PREFERENCES:
"""
        
        for pref in preferences[:10]:
            report += f"  • {pref['key']}: {pref['value']} (confidence: {pref['confidence']:.2f})\n"
        
        report += "\nTOP PATTERNS:\n"
        
        for pattern in patterns[:10]:
            report += f"  • {pattern['type']}: {pattern['data']} (frequency: {pattern['frequency']})\n"
        
        return report
