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
Your goal is to detect and identify significant environmental sounds from the provided audio, including those from a distance.

Pay extra attention to sounds like:
- Doorbells or door knocks
- Sirens (emergency vehicles)
- Bicycle bells behind or near the user
- Distant voices calling for attention
- Approaching vehicles (buses, cars, trucks)

Analyze the audio and return a JSON object with:
- "sound_event": Clear, concise identification of the primary sound (e.g., "Doorbell ringing", "Distant siren").
- "urgency": "Critical", "Caution", or "Safe".
- "guidance": Actionable advice for the user (e.g., "Someone is at the door. Please check your entrance.").

IMPORTANT: Be sensitive to background noise and focus on events that impact safety or social interaction. Detect sounds even if they appear faint or distant."""

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
        return await self._gemini_json(prompt, parts, schema)

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
