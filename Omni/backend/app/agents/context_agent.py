"""
Context Agent — A2A/0.3
Responsible for merging sensor data into a unified environmental context.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Deque
from collections import deque

logger = logging.getLogger("visionguide.context")

class ContextAgent:
    def __init__(self, memory_depth: int = 10):
        self.memory: Deque[Dict] = deque(maxlen=memory_depth)

    async def process_observations(
        self,
        vision_result: Optional[Dict] = None,
        audio_result: Optional[Dict] = None,
        nav_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Combines raw agent outputs into a unified context object.
        """
        scene = (vision_result or {}).get("scene", "")
        hazard = (vision_result or {}).get("hazard", "")
        sound_type = (audio_result or {}).get("sound_type", "none")
        audio_guidance = (audio_result or {}).get("guidance", "")
        
        # Simple safety heuristic
        safety_levels = {
            "Safe": 1, "Caution": 2, "Danger": 3,
            "Critical": 3, "none": 1, "Unknown": 1
        }
        
        v_safety = safety_levels.get((vision_result or {}).get("safety_level", "Safe"), 1)
        a_safety = safety_levels.get((audio_result or {}).get("urgency", "none"), 1)
        
        combined_score = max(v_safety, a_safety)
        unified_safety = {3: "Danger", 2: "Caution", 1: "Safe"}.get(combined_score, "Safe")

        context = {
            "unified_safety": unified_safety,
            "scene_description": scene,
            "detected_hazards": hazard,
            "environmental_sounds": sound_type,
            "audio_details": audio_guidance,
            "navigation_state": (nav_result or {}).get("instruction", "")
        }
        
        self.memory.append(context)
        return context
