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
_SYSTEM_VISION = """You are an expert Vision Accessibility Assistant for users who are blind or low vision.
Your goal is to detect and identify significant environmental details from the provided image and provide direct, actionable navigation guidance and answers to user questions.

Pay extra attention to things like:
- Obstacles, barriers, drop-offs, or hazards in the path.
- Clear paths for walking. Provide directions like "Walk straight for 5 steps", "Turn slightly left to avoid the chair", etc.
- Text such as signs, book pages, or medication labels (Read any text present).
- Nature elements to describe vivid and evocative details of the environment.

CRITICAL: If the user asks a specific question in the "User's question/context", answer it directly and accurately based ONLY on the visual information.

Analyze the image and return a JSON object with:
- "scene": Vivid, evocative description of the environment. If the user asked a question, include the direct answer here.
- "hazard": Any immediate danger, or "None detected".
- "safety_level": "Safe", "Caution", or "Danger".
- "guidance": Direct, actionable navigation advice (e.g., "Step to the right", "Path is clear for 10 feet") and weather-related advice if applicable.
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
