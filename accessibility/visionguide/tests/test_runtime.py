import sys
import os
import asyncio
# Add the current directory to sys.path to allow importing from agents and orchestrator
sys.path.append(os.getcwd())

from orchestrator.agent_runtime import AgentRuntime
from PIL import Image
import io

def test_modular_runtime():
    async def run_tests():
        print("🚀 Testing Modular Agent Runtime...")
        runtime = AgentRuntime()
        
        # Test Vision with mock (no API key/test image)
        print("\n1. Testing Vision Agent...")
        img = Image.new('RGB', (100, 100), color = 'blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        vision_result = await runtime.vision_agent.analyze(img_bytes)
        print(f"Vision Result: {vision_result}")
        
        # Test Audio with mock
        print("\n2. Testing Audio Agent...")
        audio_result = await runtime.audio_agent.analyze(b"dummy_audio_content")
        print(f"Audio Result: {audio_result}")
        
        scene_result = await runtime.analyze_scene(image_data=img_bytes)
        if 'vision' in scene_result:
            print("\n✅ Orchestrator Vision Integration: Success!")
        
        audio_scene_result = await runtime.analyze_scene(audio_data=b"dummy")
        if 'audio' in audio_scene_result:
            print("✅ Orchestrator Audio Integration: Success!")

    asyncio.run(run_tests())

if __name__ == "__main__":
    test_modular_runtime()
