import asyncio
import json
from app.agents.context_agent import ContextAgent
from app.agents.accessibility_agent import AccessibilityAgent

async def test_unified_pipeline():
    print("Testing Unified Multimodal Pipeline...")
    
    context_agent = ContextAgent()
    accessibility_agent = AccessibilityAgent()
    
    # Simulate Vision Result (Reverted Schema)
    vision_result = {
        "agent": "vision_agent",
        "scene": "a hallway with a trash can and a low-hanging branch.",
        "safety_level": "Caution",
        "hazard": "low-hanging branch",
        "confidence": 0.95,
        "guidance": "Watch your head for the branch."
    }
    
    # Simulate Audio Result (SDD Schema)
    audio_result = {
        "agent": "audio_agent",
        "event_detected": True,
        "sound_type": "vehicle_horn",
        "sound_event": "vehicle_horn",
        "urgency": "Urgent",
        "confidence": 0.88,
        "guidance": "Loud vehicle horn heard nearby."
    }
    
    print("\nProcessing observations...")
    unified_context = await context_agent.process_observations(
        vision_result=vision_result,
        audio_result=audio_result
    )
    
    print(f"Unified Safety Level: {unified_context['unified_safety']}")
    print(f"Scene: {unified_context['scene_description']}")
    print(f"Hazard: {unified_context['detected_hazards']}")
    
    print("\nGenerating final guidance...")
    final_guidance = await accessibility_agent.generate_guidance(unified_context)
    print(f"Final guidance string: \"{final_guidance}\"")
    
    # Expectations
    assert "Caution: low-hanging branch." in final_guidance
    assert "Alert: Loud vehicle horn heard nearby." in final_guidance
    assert unified_context['unified_safety'] == "Danger" # Urgent (3) > Caution (2)

    
    print("\nPipeline test PASSED!")

if __name__ == "__main__":
    asyncio.run(test_unified_pipeline())
