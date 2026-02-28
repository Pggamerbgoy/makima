"""
Pattern Analyzer - Discovers patterns in user behavior
"""
from typing import List, Dict, Any
from collections import Counter, defaultdict
from datetime import datetime
import re


class PatternAnalyzer:
    """
    Analyzes interactions to find patterns
    """
    def __init__(self):
        self.min_pattern_frequency = 3
    
    def analyze_interactions(self, interactions: List[Dict]) -> List[Dict]:
        """
        Find patterns in interactions
        
        Returns list of discovered patterns
        """
        patterns = []
        
        # Time-based patterns
        patterns.extend(self.find_time_patterns(interactions))
        
        # Command patterns
        patterns.extend(self.find_command_patterns(interactions))
        
        # Context patterns
        patterns.extend(self.find_context_patterns(interactions))
        
        # Response preference patterns
        patterns.extend(self.find_response_patterns(interactions))
        
        return patterns
    
    def find_time_patterns(self, interactions: List[Dict]) -> List[Dict]:
        """
        Find time-based patterns (e.g., "always does X at Y time")
        """
        patterns = []
        
        # Group by hour and command
        hour_commands = defaultdict(Counter)
        
        for interaction in interactions:
            try:
                timestamp = datetime.fromisoformat(interaction['timestamp'])
                hour = timestamp.hour
                command = self.extract_command_type(interaction['user_input'])
                
                hour_commands[hour][command] += 1
            except:
                continue
        
        # Find patterns
        for hour, commands in hour_commands.items():
            for command, count in commands.items():
                if count >= self.min_pattern_frequency:
                    patterns.append({
                        'type': 'time_based',
                        'pattern': f"{command} at {hour}:00",
                        'data': {
                            'hour': hour,
                            'command': command,
                            'frequency': count
                        },
                        'confidence': min(count / 10, 1.0)
                    })
        
        return patterns
    
    def find_command_patterns(self, interactions: List[Dict]) -> List[Dict]:
        """
        Find common command sequences
        """
        patterns = []
        
        # Extract command sequences
        sequences = []
        for i in range(len(interactions) - 1):
            cmd1 = self.extract_command_type(interactions[i]['user_input'])
            cmd2 = self.extract_command_type(interactions[i + 1]['user_input'])
            
            # Check if within 5 minutes
            try:
                time1 = datetime.fromisoformat(interactions[i]['timestamp'])
                time2 = datetime.fromisoformat(interactions[i + 1]['timestamp'])
                if (time2 - time1).total_seconds() < 300:
                    sequences.append(f"{cmd1} → {cmd2}")
            except:
                continue
        
        # Count sequences
        sequence_counts = Counter(sequences)
        
        for sequence, count in sequence_counts.items():
            if count >= self.min_pattern_frequency:
                patterns.append({
                    'type': 'command_sequence',
                    'pattern': sequence,
                    'data': {
                        'sequence': sequence.split(' → '),
                        'frequency': count
                    },
                    'confidence': min(count / 10, 1.0)
                })
        
        return patterns
    
    def find_context_patterns(self, interactions: List[Dict]) -> List[Dict]:
        """
        Find context-based patterns (e.g., "always plays music when coding")
        """
        patterns = []
        
        # Group by context and command
        context_commands = defaultdict(Counter)
        
        for interaction in interactions:
            try:
                context = interaction.get('context', {})
                active_app = context.get('active_window', '').lower()
                command = self.extract_command_type(interaction['user_input'])
                
                if active_app:
                    context_commands[active_app][command] += 1
            except:
                continue
        
        # Find patterns
        for app, commands in context_commands.items():
            for command, count in commands.items():
                if count >= self.min_pattern_frequency:
                    patterns.append({
                        'type': 'context_based',
                        'pattern': f"{command} when using {app}",
                        'data': {
                            'context': app,
                            'command': command,
                            'frequency': count
                        },
                        'confidence': min(count / 10, 1.0)
                    })
        
        return patterns
    
    def find_response_patterns(self, interactions: List[Dict]) -> List[Dict]:
        """
        Find preferred response styles
        """
        patterns = []
        
        # Analyze response lengths preference
        response_lengths = []
        for interaction in interactions:
            if interaction.get('user_satisfaction'):
                response_len = len(interaction['ai_response'])
                satisfaction = interaction['user_satisfaction']
                response_lengths.append((response_len, satisfaction))
        
        if len(response_lengths) >= 10:
            # Find average preferred length
            satisfied = [length for length, sat in response_lengths if sat >= 4]
            if satisfied:
                avg_preferred = sum(satisfied) / len(satisfied)
                
                if avg_preferred < 200:
                    style = 'concise'
                elif avg_preferred < 500:
                    style = 'moderate'
                else:
                    style = 'detailed'
                
                patterns.append({
                    'type': 'response_style',
                    'pattern': f"prefers {style} responses",
                    'data': {
                        'preferred_style': style,
                        'avg_length': int(avg_preferred)
                    },
                    'confidence': 0.7
                })
        
        return patterns
    
    def extract_command_type(self, user_input: str) -> str:
        """
        Extract command type from user input
        """
        user_input = user_input.lower()
        
        # Define command patterns
        if any(word in user_input for word in ['play', 'music', 'song']):
            return 'play_music'
        elif any(word in user_input for word in ['email', 'mail', 'send']):
            return 'email'
        elif any(word in user_input for word in ['calendar', 'schedule', 'meeting']):
            return 'calendar'
        elif any(word in user_input for word in ['file', 'open', 'save']):
            return 'file_operation'
        elif any(word in user_input for word in ['search', 'find', 'look']):
            return 'search'
        elif any(word in user_input for word in ['code', 'program', 'script']):
            return 'coding'
        else:
            return 'general'
    
    def get_top_patterns(self, patterns: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        Get top N patterns by confidence
        """
        sorted_patterns = sorted(patterns, key=lambda x: x['confidence'], reverse=True)
        return sorted_patterns[:top_n]
