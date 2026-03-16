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

Priority: Awareness and Recall. It is better to report a potential sound than to miss one.

Rules:
1. Report any distinct sound event you can hear. 
2. If you hear a sound but are not 100% sure of its type, use "unknown_sound" and describe it in the guidance.
3. If no significant sound is detected at all, return "none".
4. Be extremely sensitive to brief pulses, distant sirens, or mixed background noises.

Detect sounds such as:
fire_alarm, emergency_siren, vehicle_horn, approaching_vehicle,
door_knock, speech_nearby, footsteps, loud_crash, unknown_sound.

Urgency levels: Safe | Caution | Danger | Critical

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
        # Initial schema for _gemini_json, also used as a fallback
        initial_schema = {
            "agent": "audio_agent",
            "event_detected": False,
            "sound_type": "none",
            "urgency": "none",
            "confidence": 0.0,
            "guidance": "No important environmental sounds detected.",
        }
        if not self.client:
            # Mock response for when client is not available
            return {
                **initial_schema,
                "sound_type": "Mock: silence",
                "sound_event": "Mock: silence", # Alias for frontend
                "urgency": "Safe",
                "confidence": 0.5,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

        import datetime
        
        prompt = _SYSTEM_AUDIO
        if senior_mode:
            prompt += "\n\nSENIOR MODE: Use warm, patient language."
        if language != "en":
            lang_map = {"fr": "French", "hi": "Hindi", "or": "Odia"}
            prompt += f"\n\nRespond in {lang_map.get(language, 'English')}."

        audio_bytes = base64.b64decode(audio_b64)
        clean_mime = mime_type.split(";")[0].strip() or "audio/webm"
        parts = [types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)]
        
        res = await self._gemini_json(prompt, parts, initial_schema)
        res["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Save audio to GCS for persistence
        from app.core.cloud_manager import cloud_manager
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        cloud_manager.upload_blob(
            bucket_name="visionguide-audio-logs",
            source_data=audio_bytes,
            destination_blob_name=f"audio/{timestamp_str}.webm",
            content_type=clean_mime
        )

        # Mirror sound_type to sound_event for frontend compatibility
        if "sound_type" in res:
            res["sound_event"] = res["sound_type"]
        elif "sound_event" in res:
            res["sound_type"] = res["sound_event"]
            
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
