import sys
sys.path.insert(0, "c:/code/makima_fixed")
import ollama, json

# Test 1: Short system prompt
print("=== Test 1: Short system prompt ===")
r = ollama.chat(
    model="makima-v3",
    messages=[
        {"role": "system", "content": 'You are Makima, a witty personal AI companion. Respond as JSON: {"reply":"...","emotion":"..."}'},
        {"role": "user", "content": "tell me a joke"}
    ],
    format="json",
    options={"temperature": 0.3, "num_predict": 512}
)
print("Raw:", r["message"]["content"][:500])

# Test 2: Full Makima system prompt
print("\n=== Test 2: Full Makima system prompt ===")
from core.ai_handler import AIHandler
ai = AIHandler()
reply, emotion = ai.chat("hey makima, tell me a joke")
print(f"Reply: {reply}")
print(f"Emotion: {emotion}")

# Test 3: Different question
print("\n=== Test 3: Conversational ===")
reply, emotion = ai.chat("how is your day going?")
print(f"Reply: {reply}")
print(f"Emotion: {emotion}")
