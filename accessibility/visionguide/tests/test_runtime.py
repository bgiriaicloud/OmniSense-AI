import sys
import os
# Add the current directory to sys.path to allow importing from agents and orchestrator
sys.path.append(os.getcwd())

from orchestrator.agent_runtime import AgentRuntime
from PIL import Image
import io

def test_modular_runtime():
    print("🚀 Testing Modular Agent Runtime...")
    runtime = AgentRuntime()
    
    # Test Vision with mock (no API key/test image)
    print("\n1. Testing Vision Agent...")
    img = Image.new('RGB', (100, 100), color = 'blue')
    vision_result = runtime.vision_agent.analyze(img)
    print(f"Vision Result: {vision_result}")
    
    # Test Audio with mock
    print("\n2. Testing Audio Agent...")
    audio_result = runtime.audio_agent.analyze(b"dummy_audio_content")
    print(f"Audio Result: {audio_result}")
    
    if 'vision' in runtime.analyze_scene(image_data=img):
        print("\n✅ Orchestrator Vision Integration: Success!")
    
    if 'audio' in runtime.analyze_scene(audio_data=b"dummy"):
        print("✅ Orchestrator Audio Integration: Success!")

if __name__ == "__main__":
    test_modular_runtime()
