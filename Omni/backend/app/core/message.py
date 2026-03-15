"""
A2A shared message/envelope types (dataclass-based, no pydantic required).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class A2ASkillSchema:
    input: str
    output: str


@dataclass
class A2ASkill:
    id: str
    schema: A2ASkillSchema

    def to_dict(self) -> Dict:
        return {"id": self.id, "schema": {"input": self.schema.input, "output": self.schema.output}}


@dataclass
class RPCRequest:
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    jsonrpc: str = "2.0"


@dataclass
class RPCResponse:
    result: Any
    id: str
    jsonrpc: str = "2.0"


@dataclass
class RPCError:
    code: int
    message: str
    id: Optional[str] = None
    jsonrpc: str = "2.0"


# Canonical skill definitions used by all agents
VISION_SKILLS: List[Dict] = [
    A2ASkill("analyze_frame",  A2ASkillSchema("image/jpeg", "application/json")).to_dict(),
    A2ASkill("detect_hazards", A2ASkillSchema("image/jpeg", "application/json")).to_dict(),
]

AUDIO_SKILLS: List[Dict] = [
    A2ASkill("monitor_ambient", A2ASkillSchema("audio/webm", "application/json")).to_dict(),
    A2ASkill("detect_alerts",   A2ASkillSchema("audio/webm", "application/json")).to_dict(),
]

NAV_SKILLS: List[Dict] = [
    A2ASkill("calculate_heading", A2ASkillSchema("application/json", "application/json")).to_dict(),
    A2ASkill("generate_haptics",  A2ASkillSchema("application/json", "application/json")).to_dict(),
]

ORCHESTRATOR_SKILLS: List[Dict] = [
    A2ASkill("route_message",  A2ASkillSchema("application/json", "application/json")).to_dict(),
    A2ASkill("merge_context",  A2ASkillSchema("application/json", "application/json")).to_dict(),
]
