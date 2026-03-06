import threading
import time
import queue
import sys
import os
from unittest.mock import MagicMock

# Add root to path
sys.path.append(os.getcwd())

# Patch MakimaManager if it's missing 'emit' (Event system)
try:
    from core.makima_manager import MakimaManager
    if not hasattr(MakimaManager, 'emit'):
        print("⚠️ Patching MakimaManager.emit for testing")
        MakimaManager.emit = lambda self, event, *args, **kwargs: None
except ImportError:
    pass

from makima_assistant import MakimaAssistant

def test_preemption():
    print("🚀 Starting Preemption Test...")
    # Use text_mode=True to avoid microphone/audio issues
    assistant = MakimaAssistant(text_mode=True)
    
    # Patch 'hud' if missing (UI component)
    if not hasattr(assistant, 'hud'):
        print("⚠️ Patching assistant.hud for testing")
        assistant.hud = MagicMock()
    
    # ⚡ SPEED FIX: Mock AI to prevent 429 Rate Limit errors during testing
    if hasattr(assistant, 'manager') and hasattr(assistant.manager, 'ai'):
        print("⚡ Mocking AI for concurrency test (avoids 429 errors)")
        # Mock chat to return a tuple (response, emotion)
        assistant.manager.ai.chat = MagicMock(return_value=("Mock AI response", "neutral"))
        assistant.manager.ai.generate_response = MagicMock(return_value="Mock AI response")
    
    results = []
    
    def send_msg(msg, index):
        print(f"[{index}] Sending: {msg}")
        resp = assistant.process_input(msg)
        results.append((index, msg, resp))
        print(f"[{index}] Done")

    messages = [
        "What is 1+1?",
        "What is 2+2?",
        "Actually, just tell me the time."
    ]

    threads = []
    for i, msg in enumerate(messages):
        t = threading.Thread(target=send_msg, args=(msg, i))
        threads.append(t)
        t.start()
        # VERY small delay to ensure they arrive in this order, 
        # but fast enough that the worker is still busy with the first.
        time.sleep(0.05)

    for t in threads:
        t.join()

    print("\n--- Results ---")
    for index, msg, resp in sorted(results, key=lambda x: x[0]):
        print(f"[{index}] Msg: {msg} -> Resp: {resp}")

    # After the fix:
    # [0] and [1] should return None (discarded)
    # [2] should return the actual answer.

    # Check if they were processed in order
    # Note: Currently, they might finish out of order because each thread
    # calls process_input which (currently) runs synchronously in that thread.
    # After the fix, they should still finish in a way that respects the queue if we block.

if __name__ == "__main__":
    test_preemption()
