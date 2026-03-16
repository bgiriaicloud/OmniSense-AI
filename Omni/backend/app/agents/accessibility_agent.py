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
        
        # Vision guidance first
        scene = context.get("scene_description", "")
        hazard = context.get("detected_hazards", "")
        
        if hazard and hazard != "none detected":
            parts.append(f"Caution: {hazard}.")
        elif scene:
            parts.append(scene)
            
        # Audio alert
        sound = context.get("environmental_sounds")
        urgency = context.get("urgency", "none")
        if sound and sound != "none":
            audio_info = context.get("audio_details")
            if urgency in ["Critical", "Urgent", "Danger"]:
                parts.append(f"Alert: {audio_info or f'Sound of {sound} detected'}.")
            else:
                parts.append(f"Environment: {audio_info or sound}.")
            
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
