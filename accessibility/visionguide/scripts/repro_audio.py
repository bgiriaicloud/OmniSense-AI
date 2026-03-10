import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.audio_agent import AudioAgent

def test_audio():
    load_dotenv()
    agent = AudioAgent()
    
    # Create dummy audio data (empty bytes won't work for Gemini)
    # We should use a real small wav file if possible, but let's see if 
    # we can simulate the failure.
    dummy_data = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    
    print("Testing AudioAgent.analyze...")
    try:
        # Wrap the call to catch the print output in AudioAgent
        result = agent.analyze(dummy_data)
        print("\nResult:", result)
    except Exception as e:
        print("\nCaught Exception in Test Script:", e)

if __name__ == "__main__":
    test_audio()
