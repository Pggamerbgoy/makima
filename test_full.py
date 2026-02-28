import time
import os
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from core.makima_manager import MakimaManager

def run_tests():
    print('Starting Exhaustive Makima Test...')
    manager = MakimaManager(text_mode=True)
    manager.start()
    
    commands = [
        # AI & Memory
        'Hello Makima, who are you?',
        'Remember that my favorite programming language is Python.',
        'What is my favorite programming language?',
        'which ai are you using?',
        
        # System Commands
        'set volume to 30',
        'volume up',
        'volume down',
        'mute volume',
        'unmute volume',
        'battery status',
        'ram usage',
        'cpu usage',
        
        # Music
        'what is my music taste profile?',
        
        # Advanced Engines
        'simulate an investment of $10000 in Apple',
        'simulate a job change',
        'simulate a business venture',
        'set my default browser to Chrome',
        'list my preferences',
    ]
    
    with open('_test_results.log', 'w', encoding='utf-8') as f:
        for i, cmd in enumerate(commands):
            print(f'\n[{i+1}/{len(commands)}] Testing: {cmd}')
            f.write(f'\n[{i+1}/{len(commands)}] CMD: {cmd}\n')
            f.flush()
            try:
                response = manager.handle(cmd, source='text')
                print(f'➜ Response: {str(response)[:100]}...')
                f.write(f'RES: {response}\n')
            except Exception as e:
                print(f'➜ ERROR: {e}')
                f.write(f'ERR: {e}\n')
            f.flush()
            
    print('\nAll tests complete.')

if __name__ == '__main__':
    run_tests()
