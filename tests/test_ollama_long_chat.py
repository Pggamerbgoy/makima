import sys
import time
sys.path.insert(0, "c:/code/makima_fixed")
from core.ai_handler import AIHandler
from core.eternal_memory import EternalMemory

# Init with memory
mem = EternalMemory()
ai = AIHandler(memory=mem)

# Ensure Gemini is off to force Ollama
ai._is_gemini_available = lambda: False
print(f"Forcing Ollama model: {ai.ollama_model}")

messages = [
    "who are you?",
    "what do you think of me?",
    "I'm feeling a bit tired today, I was up late coding.",
    "anyway, what's a good way to stay focused while coding?",
    "can you remember that I prefer dark mode?",
    "do you remember my preference from earlier?"
]

print("\n=== STARTING LONG CHAT SIMULATION ===")
for msg in messages:
    print(f"\nUser: {msg}")
    reply, emotion = ai.chat(msg)
    print(f"Makima [{emotion}]: {reply}")
    time.sleep(1) # simulate slight delay

print("\n=== FINAL HISTORY ===")
for turn in ai.conversation_history[-4:]:
    print(f"[{turn['role']}] {turn['content'][:50]}...")
