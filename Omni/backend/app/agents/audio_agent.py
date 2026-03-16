"""
AudioAgent — A2A/0.3 + Google ADK
Skills: monitor_ambient, detect_alerts
"""
from __future__ import annotations

import base64
import logging
from typing import Any, ClassVar, Dict, List

from google.genai import types

from app.core.a2a_base import A2ABaseAgent
from app.core.message import AUDIO_SKILLS

logger = logging.getLogger("visionguide.audio")

_SYSTEM_AUDIO = """You are the Audio Agent in a multimodal accessibility system.
Your task is to analyze live microphone audio and detect environmental sounds
that may affect user awareness or safety.

Rules:
1. Only report sounds that are present in the provided audio input.
2. Do NOT guess or hallucinate sounds.
3. If confidence is low, return no_event_detected.
4. Accuracy is critical because the user may rely on this system for safety.

Detect sounds such as:
fire_alarm, emergency_siren, vehicle_horn, approaching_vehicle,
door_knock, speech_nearby, footsteps, loud_crash.

Return structured JSON:
{
  "agent": "audio_agent",
  "event_detected": true,
  "sound_type": "fire_alarm",
  "urgency": "Critical",
  "confidence": 0.95,
  "timestamp": "2024-03-21T12:00:00Z",
  "guidance": "Immediate evacuation required. Fire alarm detected."
}

If no reliable sound is detected:
{
  "agent": "audio_agent",
  "event_detected": false,
  "sound_type": "none",
  "urgency": "none",
  "confidence": 0.0,
  "guidance": "No important environmental sounds detected."
}"""


class AudioAgent(A2ABaseAgent):
    AGENT_ID: ClassVar[str] = "urn:uuid:visionguide-audio-agent"
    SKILLS: ClassVar[List[Dict]] = AUDIO_SKILLS
    ENDPOINT_PATH: ClassVar[str] = "/audio/rpc"

    def __init__(self):
        super().__init__(
            name="AudioAgent",
            description=(
                "Grounded Live Audio Agent for environmental sound detection. "
                "Identifies safety-critical audio events with strict grounding."
            ),
        )

    # ------------------------------------------------------------------
    # Skill: monitor_ambient
    # ------------------------------------------------------------------
    async def _skill_monitor_ambient(
        self,
        audio_b64: str,
        mime_type: str = "audio/webm",
        senior_mode: bool = False,
        language: str = "en",
    ) -> Dict[str, Any]:
        schema = {
            "agent": "audio_agent",
            "event_detected": False,
            "sound_type": "none",
            "urgency": "none",
            "confidence": 0.0,
            "timestamp": "2024-03-21T12:00:00Z",
            "guidance": "No important environmental sounds detected.",
        }
        if not self.client:
            return {**schema, "sound_type": "Mock: silence", "confidence": 0.5}

        import datetime
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        prompt = _SYSTEM_AUDIO
        if senior_mode:
            prompt += "\n\nSENIOR MODE: Use warm, patient language."
        if language != "en":
            lang_map = {"fr": "French", "hi": "Hindi", "or": "Odia"}
            prompt += f"\n\nRespond in {lang_map.get(language, 'English')}."

        audio_bytes = base64.b64decode(audio_b64)
        clean_mime = mime_type.split(";")[0].strip() or "audio/webm"
        parts = [types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)]
        
        res = await self._gemini_json(prompt, parts, schema)
        res["timestamp"] = timestamp
        logger.info(f"[AudioAgent] Result: {res}")
        return res

    # ------------------------------------------------------------------
    # Skill: detect_alerts
    # ------------------------------------------------------------------
    async def _skill_detect_alerts(
        self,
        audio_b64: str,
        mime_type: str = "audio/webm",
    ) -> Dict[str, Any]:
        """Legacy skill — redirected to monitor_ambient logic."""
        return await self._skill_monitor_ambient(audio_b64, mime_type)
