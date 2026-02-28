"""
Feedback Database - Stores all interactions for learning
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os


class FeedbackDatabase:
    """
    SQLite database for storing interaction feedback
    """
    def __init__(self, db_path: str = "data/feedback.db"):
        self.db_path = db_path
        
        # Create directory if needed
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """
        Create tables if they don't exist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Interactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_input TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                outcome TEXT,
                context TEXT,
                response_time REAL,
                user_satisfaction INTEGER
            )
        ''')
        
        # Preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_key TEXT UNIQUE NOT NULL,
                preference_value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                learned_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        
        # Patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("📊 Feedback database initialized")
    
    def store_interaction(self, user_input: str, ai_response: str, 
                         outcome: str = 'neutral', context: Dict = None,
                         response_time: float = 0.0, satisfaction: int = None):
        """
        Store an interaction
        
        Args:
            user_input: What the user said
            ai_response: What AI responded
            outcome: 'success', 'failure', or 'neutral'
            context: Additional context dict
            response_time: How long it took
            satisfaction: User rating (1-5) if provided
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interactions 
            (user_input, ai_response, outcome, context, response_time, user_satisfaction)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_input,
            ai_response,
            outcome,
            json.dumps(context) if context else None,
            response_time,
            satisfaction
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_interactions(self, days: int = 7, limit: int = 1000) -> List[Dict]:
        """
        Get recent interactions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM interactions
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (since_date, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to dicts
        interactions = []
        for row in rows:
            interactions.append({
                'id': row[0],
                'timestamp': row[1],
                'user_input': row[2],
                'ai_response': row[3],
                'outcome': row[4],
                'context': json.loads(row[5]) if row[5] else {},
                'response_time': row[6],
                'user_satisfaction': row[7]
            })
        
        return interactions
    
    def store_preference(self, key: str, value: str, confidence: float = 0.8):
        """
        Store a learned preference
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO learned_preferences 
            (preference_key, preference_value, confidence, learned_date)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (key, value, confidence))
        
        conn.commit()
        conn.close()
    
    def get_preference(self, key: str) -> Dict:
        """
        Get a learned preference
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM learned_preferences
            WHERE preference_key = ?
        ''', (key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'key': row[1],
                'value': row[2],
                'confidence': row[3],
                'learned_date': row[4],
                'usage_count': row[5]
            }
        
        return None
    
    def get_all_preferences(self) -> List[Dict]:
        """
        Get all learned preferences
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM learned_preferences ORDER BY confidence DESC')
        rows = cursor.fetchall()
        conn.close()
        
        preferences = []
        for row in rows:
            preferences.append({
                'key': row[1],
                'value': row[2],
                'confidence': row[3],
                'learned_date': row[4],
                'usage_count': row[5]
            })
        
        return preferences
    
    def increment_preference_usage(self, key: str):
        """
        Increment usage count for a preference
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE learned_preferences
            SET usage_count = usage_count + 1
            WHERE preference_key = ?
        ''', (key,))
        
        conn.commit()
        conn.close()
    
    def store_pattern(self, pattern_type: str, pattern_data: Dict):
        """
        Store a discovered pattern
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if pattern exists
        cursor.execute('''
            SELECT id, frequency FROM patterns
            WHERE pattern_type = ? AND pattern_data = ?
        ''', (pattern_type, json.dumps(pattern_data)))
        
        row = cursor.fetchone()
        
        if row:
            # Increment frequency
            cursor.execute('''
                UPDATE patterns
                SET frequency = frequency + 1, last_seen = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (row[0],))
        else:
            # Insert new pattern
            cursor.execute('''
                INSERT INTO patterns (pattern_type, pattern_data)
                VALUES (?, ?)
            ''', (pattern_type, json.dumps(pattern_data)))
        
        conn.commit()
        conn.close()
    
    def get_patterns(self, pattern_type: str = None, min_frequency: int = 3) -> List[Dict]:
        """
        Get discovered patterns
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if pattern_type:
            cursor.execute('''
                SELECT * FROM patterns
                WHERE pattern_type = ? AND frequency >= ?
                ORDER BY frequency DESC
            ''', (pattern_type, min_frequency))
        else:
            cursor.execute('''
                SELECT * FROM patterns
                WHERE frequency >= ?
                ORDER BY frequency DESC
            ''', (min_frequency,))
        
        rows = cursor.fetchall()
        conn.close()
        
        patterns = []
        for row in rows:
            patterns.append({
                'id': row[0],
                'type': row[1],
                'data': json.loads(row[2]),
                'frequency': row[3],
                'last_seen': row[4]
            })
        
        return patterns
    
    def get_stats(self) -> Dict:
        """
        Get database statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total interactions
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        # Success rate
        cursor.execute('''
            SELECT COUNT(*) FROM interactions WHERE outcome = 'success'
        ''')
        successful = cursor.fetchone()[0]
        success_rate = (successful / total_interactions * 100) if total_interactions > 0 else 0
        
        # Total preferences
        cursor.execute('SELECT COUNT(*) FROM learned_preferences')
        total_preferences = cursor.fetchone()[0]
        
        # Total patterns
        cursor.execute('SELECT COUNT(*) FROM patterns')
        total_patterns = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_interactions': total_interactions,
            'success_rate': round(success_rate, 2),
            'learned_preferences': total_preferences,
            'discovered_patterns': total_patterns
        }
