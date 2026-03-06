import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Makima_v4.memory.knowledge_graph import KnowledgeGraph

class TestConsistencyGuard(unittest.TestCase):
    def setUp(self):
        self.kg = KnowledgeGraph()
        # Clear existing data for a clean test if needed, 
        # but KnowledgeGraph usually loads from disk. 
        # For testing, we might want a temporary graph file.
        self.kg.file_path = "data/test_knowledge_graph.graphml"
        if os.path.exists(self.kg.file_path):
            os.remove(self.kg.file_path)
        self.kg.graph.clear()

    def test_conflict_detection(self):
        print("Testing Conflict Detection...")
        # Add a fact
        self.kg.add_edge("user", "Mumbai", "lives in")
        
        # Add a conflicting fact
        conflict = self.kg.add_edge("user", "Delhi", "lives in")
        
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict['subject'], "user")
        self.assertEqual(conflict['relationship'], "lives in")
        self.assertEqual(conflict['old_object'], "Mumbai")
        self.assertEqual(conflict['new_object'], "Delhi")
        print("✅ Conflict Detection Test Passed")

    def test_no_conflict_different_relation(self):
        print("Testing No Conflict (Different Relation)...")
        self.kg.add_edge("user", "Mumbai", "lives in")
        conflict = self.kg.add_edge("user", "Engineer", "is a")
        self.assertIsNone(conflict)
        print("✅ No Conflict (Different Relation) Test Passed")

    def tearDown(self):
        if os.path.exists(self.kg.file_path):
            os.remove(self.kg.file_path)

if __name__ == "__main__":
    unittest.main()
