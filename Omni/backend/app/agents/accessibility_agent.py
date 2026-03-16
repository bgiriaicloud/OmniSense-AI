"""
Accessibility Agent — A2A/0.3
Responsible for generating final user-facing guidance and speech synthesis prompts.
"""
from __future__ import annotations
import logging
from typing import Any, Dict

logger = logging.getLogger("visionguide.accessibility")

class AccessibilityAgent:
    def __init__(self):
        pass

    async def generate_guidance(self, context: Dict[str, Any], senior_mode: bool = False) -> str:
        """
        Converts the merged context into a polite, clear, spoken guidance string.
        """
        parts = []
        
        # Hazard first
        hazard = context.get("detected_hazards")
        if hazard and "none" not in hazard.lower():
            parts.append(f"Caution: {hazard}.")
            
        # Audio alert
        sound = context.get("environmental_sounds")
        if sound and sound != "none":
            audio_info = context.get("audio_details")
            parts.append(f"Audio alert: {audio_info or sound}.")
            
        # Navigation
        nav = context.get("navigation_state")
        if nav:
            parts.append(nav)
            
        if not parts:
            if context.get("unified_safety") == "Safe":
                parts.append("Path is clear. Surrounded by safe environment.")
            else:
                parts.append("Stay alert. Environment is changing.")

        guidance = " ".join(parts)
        
        if senior_mode:
            guidance = f"Hello there. {guidance} Take your time and stay safe."
            
        return guidance
