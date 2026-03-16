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

_SYSTEM_AMBIENT = """You are an expert Audio Accessibility Assistant for users who are deaf or hard of hearing.
Your job is to listen to the audio and describe EVERYTHING you hear, then guide the user based on it.

RULES:
1. ALWAYS describe the audio environment — even silence has information ("It is quiet around you. No sounds detected.").
2. Report sounds clearly and specifically: "I hear a car engine nearby", "There are voices in the background", "A phone is ringing".
3. Assess the safety implication of each sound.
4. Give practical, actionable guidance — never leave the user without direction.
5. Do NOT say "No guidance needed." — always provide a contextual statement even if safe.

Return a JSON object:
- "sound_event": Clear description of what you hear (e.g., "Quiet indoor environment", "Car engine approaching", "Conversation in background").
- "urgency": "Critical" (immediate danger), "Caution" (pay attention), or "Safe" (normal).
- "guidance": Specific instruction (e.g., "The area sounds quiet and safe to move.", "A vehicle is nearby — wait before crossing.", "Someone is speaking — you may want to respond.")."""

_SYSTEM_ALERTS = """You are an expert Audio Accessibility Assistant for users who are deaf or hard of hearing.
Listen for emergency sounds: alarms, sirens, smoke detectors, car horns, screams.
Return a JSON object:
  - alerts: list of detected alert sounds (empty list if none).
  - highest_urgency: "Safe", "Caution", or "Critical".
  - action: immediate instruction for the user."""


class AudioAgent(A2ABaseAgent):
    AGENT_ID: ClassVar[str] = "urn:uuid:visionguide-audio-agent"
    SKILLS: ClassVar[List[Dict]] = AUDIO_SKILLS
    ENDPOINT_PATH: ClassVar[str] = "/audio/rpc"

    def __init__(self):
        super().__init__(
            name="AudioAgent",
            description=(
                "Environmental sound detection for deaf and hard-of-hearing users. "
                "Identifies sirens, alarms, approaching vehicles, voices, and more."
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
            "sound_event": "Unknown.",
            "urgency": "Normal",
            "guidance": "No guidance.",
        }
        if not self.client:
            return {**schema, "sound_event": "Mock: ambient street noise.", "urgency": "Normal"}

        prompt = _SYSTEM_AMBIENT
        if senior_mode:
            prompt += "\n\nSENIOR MODE: Use warm, patient language."
        if language != "en":
            lang_map = {"fr": "French", "hi": "Hindi", "or": "Odia"}
            prompt += f"\n\nRespond in {lang_map.get(language, 'English')}."

        audio_bytes = base64.b64decode(audio_b64)
        clean_mime = mime_type.split(";")[0].strip() or "audio/webm"
        parts = [types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)]
        res = await self._gemini_json(prompt, parts, schema)
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
        schema = {
            "alerts": [],
            "highest_urgency": "Normal",
            "action": "Continue as normal.",
        }
        if not self.client:
            return {**schema, "alerts": [], "highest_urgency": "Normal"}

        audio_bytes = base64.b64decode(audio_b64)
        clean_mime = mime_type.split(";")[0].strip() or "audio/webm"
        parts = [types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)]
        return await self._gemini_json(_SYSTEM_ALERTS, parts, schema)
