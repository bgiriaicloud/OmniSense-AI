"""
A2A Protocol v0.3 + Google ADK BaseAgent Integration.

Provides:
  - A2ABaseAgent: abstract class wrapping adk.BaseAgent with JSON-RPC 2.0 dispatch
  - jsonrpc_request / jsonrpc_response / jsonrpc_error: message builders
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from abc import abstractmethod
from typing import Any, ClassVar, Dict, List, Optional

from dotenv import load_dotenv
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import Client
from pydantic import ConfigDict, Field
from typing import AsyncGenerator

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../..", "config", ".env"), override=True)

logger = logging.getLogger("visionguide.a2a")


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 helpers
# ---------------------------------------------------------------------------

def jsonrpc_request(method: str, params: Dict[str, Any], req_id: str | None = None) -> Dict:
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": req_id or str(uuid.uuid4()),
    }


def jsonrpc_response(result: Any, req_id: str) -> Dict:
    return {"jsonrpc": "2.0", "result": result, "id": req_id}


def jsonrpc_error(code: int, message: str, req_id: str | None = None) -> Dict:
    return {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": req_id,
    }


# ---------------------------------------------------------------------------
# A2A-compliant base agent
# ---------------------------------------------------------------------------

class A2ABaseAgent(BaseAgent):
    """
    Abstract base for all VisionGuide agents.

    Inherits from google.adk.agents.BaseAgent and adds:
      - Gemini client bootstrap from GEMINI_API_KEY
      - A2A skill dispatch (dispatch_skill)
      - Agent Card metadata (agent_card property)
    """

    # Override Pydantic config to allow our extra fields (model_id, client)
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # ClassVar so Pydantic v2 does NOT treat these as model fields
    AGENT_ID: ClassVar[str] = "urn:uuid:visionguide-base"
    AGENT_VERSION: ClassVar[str] = "1.0.0"
    SKILLS: ClassVar[List[Dict]] = []
    ENDPOINT_PATH: ClassVar[str] = "/rpc"

    # Declared as proper Optional Pydantic fields
    model_id: Optional[str] = Field(default=None, exclude=True)
    client: Optional[Any] = Field(default=None, exclude=True)

    def __init__(self, name: str, description: str, model_id: str | None = None):
        super().__init__(name=name, description=description)
        resolved_model_id = model_id or os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")
        api_key = os.getenv("GEMINI_API_KEY", "")
        # Use object.__setattr__ to bypass Pydantic strict mode for runtime-only fields
        object.__setattr__(self, "model_id", resolved_model_id)
        if api_key:
            object.__setattr__(self, "client", Client(api_key=api_key))
            logger.info("[%s] Gemini client ready (model=%s)", name, resolved_model_id)
        else:
            object.__setattr__(self, "client", None)
            logger.warning("[%s] No GEMINI_API_KEY — mock mode active", name)

    # ------------------------------------------------------------------
    # ADK mandatory override
    # ------------------------------------------------------------------
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        ADK execution hook.  Agents that need streaming override this;
        the default raises so callers know to use dispatch_skill instead.
        """
        raise NotImplementedError(f"{self.name} does not implement _run_async_impl directly; use dispatch_skill()")
        # Required by protocol — make this a proper async generator
        return
        yield  # noqa: unreachable — makes this an async generator

    # ------------------------------------------------------------------
    # A2A skill dispatch
    # ------------------------------------------------------------------
    async def dispatch_skill(self, rpc_request: Dict) -> Dict:
        """
        Receives a JSON-RPC 2.0 request and routes to the matching skill handler.
        Handlers are named  _skill_<method>  on the subclass.
        """
        req_id = rpc_request.get("id")
        method = rpc_request.get("method", "")
        params = rpc_request.get("params", {})

        handler_name = f"_skill_{method}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            return jsonrpc_error(-32601, f"Method '{method}' not found", req_id)

        try:
            result = await handler(**params)
            return jsonrpc_response(result, req_id)
        except Exception as exc:
            logger.exception("[%s] Error in skill %s", self.name, method)
            return jsonrpc_error(-32603, str(exc), req_id)

    # ------------------------------------------------------------------
    # Agent Card (A2A Discovery)
    # ------------------------------------------------------------------
    def agent_card(self, base_url: str = "http://localhost:8000") -> Dict:
        return {
            "id": self.AGENT_ID,
            "name": self.name,
            "version": self.AGENT_VERSION,
            "protocol": "A2A/0.3",
            "endpoint": f"{base_url}{self.ENDPOINT_PATH}",
            "skills": self.SKILLS,
        }

    # ------------------------------------------------------------------
    # Utility: JSON generation via Gemini with Fallback
    # ------------------------------------------------------------------
    async def _gemini_json(self, prompt: str, parts: list, schema_defaults: Dict) -> Dict:
        from google.genai import types  # type: ignore

        if not self.client:
            return schema_defaults

        # Priority list of models for dynamic mapping
        models_to_try = [
            self.model_id,
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys(m for m in models_to_try if m))

        last_err = ""
        for model_name in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[prompt] + parts,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                text = response.text.strip() if response.text else ""
                if not text:
                    raise ValueError("Empty response")
                data = json.loads(text)
                for k, v in schema_defaults.items():
                    data.setdefault(k, v)
                return data
            except Exception as exc:
                err = str(exc)
                logger.warning("[%s] Model %s failed: %s", self.name, model_name, err)
                last_err = err
                # If it's a quota issue, try the next model immediately
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    continue
                # If it's something else but we have more models, try them
                continue

        # If we get here, all models failed
        logger.error("[%s] All Gemini models failed. Last error: %s", self.name, last_err)
        if "429" in last_err or "RESOURCE_EXHAUSTED" in last_err:
            return {**schema_defaults, "guidance": "Resources exhausted on all models. Please wait a moment."}
        return {**schema_defaults, "guidance": f"System error: {last_err}"}
