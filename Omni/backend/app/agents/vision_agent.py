"""
VisionAgent — A2A/0.3 + Google ADK
Skills: analyze_frame, detect_hazards
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Any, ClassVar, Dict, List

from google import genai
from google.genai import types

from app.core.a2a_base import A2ABaseAgent
from app.core.message import VISION_SKILLS

logger = logging.getLogger("visionguide.vision")

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
_SYSTEM_VISION = """You are the Vision Agent in a multimodal accessibility system.
Your job is to provide vivid, accurate descriptions of the camera feed for visually impaired users.

RULES:
1. Only report details that are present in the provided image.
2. Do NOT guess, imagine, or hallucinate details.
3. Accuracy is critical for navigation and safety.
4. If the image is unclear or dark, report that precisely.

Analyze the image and return a JSON object with:
- "agent": "vision_agent"
- "scene": Vivid, evocative description of detected objects, people, and the environment. Answer user questions directly.
- "hazard": Specific immediate dangers (e.g., "trip hazard: chair", "slippery floor"). If none, return "None detected".
- "safety_level": "Safe", "Caution", or "Danger".
- "guidance": Actionable navigation advice (e.g., "Step to the right to avoid the bag", "Continue straight, path is clear").
Use plain, calm, spoken language."""

_SYSTEM_HAZARD = """You are VisionGuide's hazard-detection specialist.
Focus exclusively on detecting obstacles, dangerous surfaces, traffic, falls, or other risks.
Return a JSON object:
  - hazards: list of strings describing each hazard (empty list if none).
  - risk_level: one of "Low", "Medium", "High".
  - immediate_action: short imperative instruction for the user.
Be concise — response is spoken aloud."""


class VisionAgent(A2ABaseAgent):
    AGENT_ID: ClassVar[str] = "urn:uuid:visionguide-vision-agent"
    SKILLS: ClassVar[List[Dict]] = VISION_SKILLS
    ENDPOINT_PATH: ClassVar[str] = "/vision/rpc"

    def __init__(self):
        super().__init__(
            name="VisionAgent",
            description=(
                "Real-time camera frame analysis. Identifies scenes, obstacles, hazards, "
                "and navigation cues for visually impaired users."
            ),
        )

    # ------------------------------------------------------------------
    # Skill: analyze_frame
    # ------------------------------------------------------------------
    async def _skill_analyze_frame(
        self,
        image_b64: str,
        query: str = "Describe my surroundings.",
        senior_mode: bool = False,
        language: str = "en",
    ) -> Dict[str, Any]:
        schema = {
            "agent": "vision_agent",
            "scene": "Scene unavailable.",
            "hazard": "No hazard info.",
            "guidance": "No guidance.",
            "safety_level": "Unknown",
        }
        if not self.client:
            return {**schema, "scene": "Mock: bright modern hallway.", "safety_level": "Safe"}

        prompt = _SYSTEM_VISION
        if query:
            prompt += f"\n\nUser's question/context: {query}"
        if senior_mode:
            prompt += "\n\nSENIOR MODE: Use a warm, encouraging tone. Add a brief wellness reminder."
        if language != "en":
            lang_map = {"fr": "French", "hi": "Hindi", "or": "Odia"}
            prompt += f"\n\nRespond in {lang_map.get(language, 'English')}."

        image_bytes = base64.b64decode(image_b64)
        
        # Upload to GCS for persistence/logging
        from app.core.cloud_manager import cloud_manager
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        cloud_manager.upload_blob(
            bucket_name="visionguide-snapshots",
            source_data=image_bytes,
            destination_blob_name=f"vision/{timestamp}.jpg"
        )

        parts = [types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")]
        return await self._gemini_json(prompt, parts, schema)

    # ------------------------------------------------------------------
    # Skill: detect_hazards
    # ------------------------------------------------------------------
    async def _skill_detect_hazards(
        self,
        image_b64: str,
    ) -> Dict[str, Any]:
        schema = {
            "hazards": [],
            "risk_level": "Unknown",
            "immediate_action": "Proceed with caution.",
        }
        if not self.client:
            return {**schema, "hazards": ["Mock: clear path"], "risk_level": "Low"}

        image_bytes = base64.b64decode(image_b64)
        parts = [types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")]
        return await self._gemini_json(_SYSTEM_HAZARD, parts, schema)
