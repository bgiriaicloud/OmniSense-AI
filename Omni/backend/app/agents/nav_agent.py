"""
NavAgent — A2A/0.3 + Google ADK
Skills: calculate_heading, generate_haptics
"""
from __future__ import annotations

import logging
import math
from typing import Any, ClassVar, Dict, List, Optional

from app.core.a2a_base import A2ABaseAgent, jsonrpc_response
from app.core.message import NAV_SKILLS

logger = logging.getLogger("visionguide.nav")

# Compass directions
_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Haptic patterns (duration ms, gap ms, repeat)
_HAPTIC_PATTERNS: Dict[str, List[int]] = {
    "straight":    [100, 50, 100, 50, 100],   # 3 short pulses
    "turn_left":   [500, 100, 100],            # 1 long, 1 short
    "turn_right":  [100, 100, 500],            # 1 short, 1 long
    "stop":        [1000],                     # 1 long hold
    "hazard":      [200, 100, 200, 100, 200, 100, 200],  # SOS-like
    "arrive":      [100, 50, 100, 50, 100, 50, 500],
}


class NavAgent(A2ABaseAgent):
    AGENT_ID: ClassVar[str] = "urn:uuid:visionguide-nav-agent"
    SKILLS: ClassVar[List[Dict]] = NAV_SKILLS
    ENDPOINT_PATH: ClassVar[str] = "/nav/rpc"

    def __init__(self):
        super().__init__(
            name="NavAgent",
            description="Pathfinding and haptic-guide logic for VisionGuide navigation.",
        )

    # ------------------------------------------------------------------
    # Skill: calculate_heading
    # ------------------------------------------------------------------
    async def _skill_calculate_heading(
        self,
        current_lat: float,
        current_lon: float,
        target_lat: float,
        target_lon: float,
        obstacle_context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Computes compass bearing, distance, and spoken turn instruction
        from current position to target.
        """
        d_lat = math.radians(target_lat - current_lat)
        d_lon = math.radians(target_lon - current_lon)
        lat1 = math.radians(current_lat)
        lat2 = math.radians(target_lat)

        # Haversine distance (metres)
        a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
        distance_m = round(6_371_000 * 2 * math.asin(math.sqrt(a)), 1)

        # Bearing (degrees, 0 = North)
        x = math.sin(d_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        bearing_deg = (math.degrees(math.atan2(x, y)) + 360) % 360

        compass_idx = round(bearing_deg / 45) % 8
        compass_dir = _COMPASS[compass_idx]

        # Simple spoken instruction
        if distance_m < 5:
            instruction = "You have arrived at your destination."
            maneuver = "arrive"
        elif bearing_deg < 22.5 or bearing_deg > 337.5:
            instruction = f"Continue straight for {distance_m:.0f} metres."
            maneuver = "straight"
        elif bearing_deg < 180:
            instruction = f"Turn right and continue {distance_m:.0f} metres."
            maneuver = "turn_right"
        else:
            instruction = f"Turn left and continue {distance_m:.0f} metres."
            maneuver = "turn_left"

        # Overlay hazard warning if present
        if obstacle_context and obstacle_context.get("risk_level") in ("Medium", "High"):
            instruction = f"⚠ Hazard ahead — {obstacle_context.get('immediate_action', 'stop')}. " + instruction
            maneuver = "hazard"

        return {
            "bearing_degrees": round(bearing_deg, 1),
            "compass": compass_dir,
            "distance_metres": distance_m,
            "instruction": instruction,
            "maneuver": maneuver,
        }

    # ------------------------------------------------------------------
    # Skill: generate_haptics
    # ------------------------------------------------------------------
    async def _skill_generate_haptics(
        self,
        maneuver: str = "straight",
        intensity: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Returns a haptic pattern for the given maneuver type.
        intensity ∈ [0.0, 1.0] scales pulse durations.
        """
        pattern = _HAPTIC_PATTERNS.get(maneuver, _HAPTIC_PATTERNS["straight"])
        scaled = [round(d * max(0.1, min(1.0, intensity))) for d in pattern]
        return {
            "maneuver": maneuver,
            "pattern_ms": scaled,
            "description": f"Haptic pattern for '{maneuver}' at {intensity*100:.0f}% intensity.",
        }
