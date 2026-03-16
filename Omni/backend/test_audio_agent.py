
import asyncio
import os
import base64
from app.agents.audio_agent import AudioAgent

async def test_audio():
    agent = AudioAgent()
    print(f"Testing AudioAgent: {agent.name}")
    
    # Mock audio (short silent webm-like header or just random bytes for testing mock mode)
    mock_audio_b64 = base64.b64encode(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00").decode()
    
    print("Dispatching monitor_ambient...")
    result = await agent.dispatch_skill({
        "jsonrpc": "2.0",
        "method": "monitor_ambient",
        "params": {
            "audio_b64": mock_audio_b64,
            "mime_type": "audio/webm"
        },
        "id": "1"
    })
    print("Result:", result)
    if "result" in result:
        res = result["result"]
        assert "sound_type" in res
        assert "sound_event" in res
        assert "urgency" in res
        print("Success: sound_type and sound_event found in response.")

if __name__ == "__main__":
    asyncio.run(test_audio())
