"""
Orchestrator — A2A/0.3 + Google ADK
Skills: route_message, merge_context
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any, ClassVar, Deque, Dict, List, Optional

from app.core.a2a_base import A2ABaseAgent, jsonrpc_error
from app.core.message import ORCHESTRATOR_SKILLS
from app.agents.context_agent import ContextAgent
from app.agents.accessibility_agent import AccessibilityAgent

logger = logging.getLogger("visionguide.orchestrator")


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
            description="A2A Router & Multi-Agent Orchestrator for VisionGuide.",
        )
        self._agents: Dict[str, A2ABaseAgent] = {}
        if vision_agent: self._agents["vision"] = vision_agent
        if audio_agent:  self._agents["audio"] = audio_agent
        if nav_agent:    self._agents["nav"] = nav_agent

        # New Cooperating Agents
        self.context_agent = ContextAgent()
        self.accessibility_agent = AccessibilityAgent()

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
        Cooperative flow: 
        Sensor Agents -> ContextAgent -> AccessibilityAgent
        """
        # 1. Build unified context via ContextAgent
        context = await self.context_agent.process_observations(
            vision_result=vision_result,
            audio_result=audio_result,
            nav_result=nav_result
        )

        # 2. Generate final guidance via AccessibilityAgent
        spoken_guidance = await self.accessibility_agent.generate_guidance(
            context=context,
            senior_mode=senior_mode
        )

        # 3. Publish alerts if needed
        hazard = context.get("detected_hazards")
        if hazard and "none" not in hazard.lower():
            from app.core.cloud_manager import cloud_manager
            cloud_manager.publish_alert("hazard-alerts", {
                "hazard": hazard,
                "unified_safety": context.get("unified_safety")
            })

        # Return the merged state
        return {
            **context,
            "spoken_guidance": spoken_guidance,
            "senior_mode": senior_mode
        }

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
        session_id: Optional[str] = None,
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
                "session_id": session_id,
            })
            resp = await self._agents["vision"].dispatch_skill(rpc)
            vision_result = resp.get("result")

        if audio_b64 and "audio" in self._agents:
            rpc = jsonrpc_request("monitor_ambient", {
                "audio_b64": audio_b64,
                "mime_type": audio_mime,
                "senior_mode": senior_mode,
                "language": language,
                "session_id": session_id,
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
