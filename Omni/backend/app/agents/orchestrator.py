"""
Orchestrator — A2A/0.3 + Google ADK
Skills: route_message, merge_context

The Orchestrator acts as the central A2A router:
  - route_message: dispatches an incoming JSON-RPC call to the correct agent
  - merge_context: combines outputs from VisionAgent + AudioAgent + NavAgent
    into a unified accessibility context object
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any, ClassVar, Deque, Dict, List, Optional

from app.core.a2a_base import A2ABaseAgent, jsonrpc_error
from app.core.message import ORCHESTRATOR_SKILLS

logger = logging.getLogger("visionguide.orchestrator")

# How many past observations to keep in memory
_MAX_MEMORY = 10


class Orchestrator(A2ABaseAgent):
    AGENT_ID: ClassVar[str] = "urn:uuid:visionguide-orchestrator"
    SKILLS: ClassVar[List[Dict]] = ORCHESTRATOR_SKILLS
    ENDPOINT_PATH: ClassVar[str] = "/orchestrator/rpc"

    def __init__(
        self,
        vision_agent=None,
        audio_agent=None,
        nav_agent=None,
    ):
        super().__init__(
            name="Orchestrator",
            description="A2A Router & Context Merger for VisionGuide multi-agent system.",
        )
        # Agent registry (populated by main.py)
        self._agents: Dict[str, A2ABaseAgent] = {}
        if vision_agent:
            self._agents["vision"] = vision_agent
        if audio_agent:
            self._agents["audio"] = audio_agent
        if nav_agent:
            self._agents["nav"] = nav_agent

        # Rolling memory of merged contexts
        self._memory: Deque[Dict] = deque(maxlen=_MAX_MEMORY)

    # ------------------------------------------------------------------
    # Skill: route_message
    # ------------------------------------------------------------------
    async def _skill_route_message(
        self,
        target_agent: str,
        rpc_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Forwards a JSON-RPC 2.0 request to the named sub-agent and returns
        its JSON-RPC response.  target_agent ∈ {"vision","audio","nav"}.
        """
        agent = self._agents.get(target_agent)
        if agent is None:
            return jsonrpc_error(-32601, f"Unknown agent '{target_agent}'", rpc_request.get("id"))

        logger.info("[Orchestrator] Routing → %s :: %s", target_agent, rpc_request.get("method"))
        return await agent.dispatch_skill(rpc_request)

    # ------------------------------------------------------------------
    # Skill: merge_context
    # ------------------------------------------------------------------
    async def _skill_merge_context(
        self,
        vision_result: Optional[Dict] = None,
        audio_result: Optional[Dict] = None,
        nav_result: Optional[Dict] = None,
        senior_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Merges the outputs from multiple agents into a single unified context
        and stores it in rolling memory.
        """
        # --- Safety level aggregation ---
        safety_map = {"Danger": 3, "Caution": 2, "Safe": 1, "Unknown": 0}
        urgency_map = {"Critical": 3, "Caution": 2, "Safe": 1, "none": 1}

        vision_safety = safety_map.get(
            (vision_result or {}).get("safety_level", "Unknown"), 0
        )
        audio_urgency = urgency_map.get(
            (audio_result or {}).get("urgency", "none"), 1
        )

        # Unified safety level
        combined_score = max(vision_safety, audio_urgency)
        unified_safety = {3: "Danger", 2: "Caution", 1: "Safe", 0: "Unknown"}.get(
            combined_score, "Unknown"
        )

        # --- Build merged output ---
        scene = (vision_result or {}).get("scene", "")
        hazard = (vision_result or {}).get("hazard", "")
        sound_type = (audio_result or {}).get("sound_type", "none")
        audio_guidance = (audio_result or {}).get("guidance", "")
        nav_instruction = (nav_result or {}).get("instruction", "")

        # Persistent hazard detection from memory
        recent_hazards = [m.get("hazard", "") for m in self._memory if m.get("hazard")]
        is_persistent = any(
            h and h.lower() not in ("none detected", "no hazard info.")
            for h in recent_hazards[-3:]
        )

        # Compose spoken guidance
        parts: List[str] = []
        if hazard and hazard.lower() not in ("none detected", "no hazard info."):
            if is_persistent:
                parts.append(f"⚠ Persistent hazard: {hazard}.")
            else:
                parts.append(f"Hazard: {hazard}.")
        
        if sound_type and sound_type != "none":
            parts.append(f"Audio Alert: {audio_guidance or sound_type}.")
        
        if nav_instruction:
            parts.append(nav_instruction)

        spoken_guidance = " ".join(parts) if parts else "All clear — surroundings appear safe."

        if hazard and hazard.lower() not in ("none detected", "no hazard info."):
            from app.core.cloud_manager import cloud_manager
            cloud_manager.publish_alert("hazard-alerts", {
                "hazard": hazard,
                "scene": scene,
                "unified_safety": unified_safety,
                "is_persistent": is_persistent
            })

        merged = {
            "unified_safety": unified_safety,
            "scene": scene,
            "hazard": hazard,
            "sound_type": sound_type,
            "audio_guidance": audio_guidance,
            "nav_instruction": nav_instruction,
            "spoken_guidance": spoken_guidance,
            "is_persistent_hazard": is_persistent,
            "senior_mode": senior_mode,
            "memory_depth": len(self._memory),
        }

        # Persist in rolling memory
        self._memory.append(merged)
        return merged

    # ------------------------------------------------------------------
    # Convenience: full pipeline
    # ------------------------------------------------------------------
    async def analyze_scene(
        self,
        image_b64: Optional[str] = None,
        audio_b64: Optional[str] = None,
        audio_mime: str = "audio/webm",
        query: str = "Describe my surroundings.",
        senior_mode: bool = False,
        language: str = "en",
        nav_params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method called by the FastAPI main endpoint.
        Runs all applicable agents and merges results.
        """
        from app.core.a2a_base import jsonrpc_request

        vision_result = None
        audio_result = None
        nav_result = None

        if image_b64 and "vision" in self._agents:
            rpc = jsonrpc_request("analyze_frame", {
                "image_b64": image_b64,
                "query": query,
                "senior_mode": senior_mode,
                "language": language,
            })
            resp = await self._agents["vision"].dispatch_skill(rpc)
            vision_result = resp.get("result")

        if audio_b64 and "audio" in self._agents:
            rpc = jsonrpc_request("monitor_ambient", {
                "audio_b64": audio_b64,
                "mime_type": audio_mime,
                "senior_mode": senior_mode,
                "language": language,
            })
            resp = await self._agents["audio"].dispatch_skill(rpc)
            audio_result = resp.get("result")

        if nav_params and "nav" in self._agents:
            rpc = jsonrpc_request("calculate_heading", nav_params)
            resp = await self._agents["nav"].dispatch_skill(rpc)
            nav_result = resp.get("result")

        return await self._skill_merge_context(
            vision_result=vision_result,
            audio_result=audio_result,
            nav_result=nav_result,
            senior_mode=senior_mode,
        )
