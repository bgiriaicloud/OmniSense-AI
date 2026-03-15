"""
VisionGuide AI — FastAPI Server
A2A Protocol v0.3 | Google ADK | JSON-RPC 2.0

Endpoints:
  POST /vision/rpc        — VisionAgent JSON-RPC
  POST /audio/rpc         — AudioAgent JSON-RPC
  POST /nav/rpc           — NavAgent JSON-RPC
  POST /orchestrator/rpc  — Orchestrator JSON-RPC

  GET  /.well-known/agent.json               — Orchestrator card
  GET  /vision/.well-known/agent.json        — VisionAgent card
  GET  /audio/.well-known/agent.json         — AudioAgent card
  GET  /nav/.well-known/agent.json           — NavAgent card

  POST /analyze           — High-level convenience: image+audio pipeline
  POST /analyze/vision    — Single image analysis
  POST /analyze/audio     — Single audio analysis
  POST /nav/heading       — Point-to-point heading
  POST /nav/haptics       — Haptic pattern for maneuver
  GET  /health            — Server health
"""
from __future__ import annotations

import base64
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Load .env (config folder lives at project root)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "config", ".env")
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("visionguide.main")

# Lazy-import agents so env vars are loaded first
from app.agents.vision_agent import VisionAgent
from app.agents.audio_agent import AudioAgent
from app.agents.nav_agent import NavAgent
from app.agents.orchestrator import Orchestrator

# ---------------------------------------------------------------------------
# Application singleton & lifespan
# ---------------------------------------------------------------------------
vision_agent: VisionAgent
audio_agent: AudioAgent
nav_agent: NavAgent
orchestrator: Orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vision_agent, audio_agent, nav_agent, orchestrator
    logger.info("Initializing VisionGuide agents…")
    vision_agent = VisionAgent()
    audio_agent = AudioAgent()
    nav_agent = NavAgent()
    orchestrator = Orchestrator(
        vision_agent=vision_agent,
        audio_agent=audio_agent,
        nav_agent=nav_agent,
    )
    logger.info("All agents online.")
    yield
    logger.info("Shutdown complete.")


app = FastAPI(
    title="VisionGuide AI",
    description="Multi-agent accessibility platform — A2A v0.3 + Google ADK",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    from google import genai
    from google.genai import types
    import asyncio
    
    client = genai.Client()
    model = os.getenv("GEMINI_LIVE_MODEL_ID", "gemini-2.5-flash-native-audio-latest")
    
    config = {"response_modalities": ["AUDIO"]}
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            await session.send(input="Please analyze the video and audio streams I send. Warn me of any hazards or alerts since I am hearing impaired.", end_of_turn=True)
            
            async def receive_from_client():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        if not data:
                            break
                        msg_type = data[0]
                        payload = data[1:]
                        if msg_type == 1: # Video
                            await session.send(input={"mime_type": "image/jpeg", "data": payload})
                        elif msg_type == 2: # Audio
                            await session.send(input={"mime_type": "audio/webm", "data": payload})
                except Exception as e:
                    logger.error(f"WS client error: {e}")
                    
            async def receive_from_gemini():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    await websocket.send_bytes(part.inline_data.data)
                except Exception as e:
                    logger.error(f"WS gemini error: {e}")
                    
            # Run both bridging tasks concurrently
            await asyncio.gather(receive_from_client(), receive_from_gemini())
    except Exception as e:
        logger.error(f"Live API connection error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass



# ===========================================================================
# Agent Card Discovery  (A2A /.well-known/agent.json)
# ===========================================================================

@app.get("/.well-known/agent.json", tags=["Discovery"])
async def orchestrator_card():
    return orchestrator.agent_card(BASE_URL)


@app.get("/vision/.well-known/agent.json", tags=["Discovery"])
async def vision_card():
    return vision_agent.agent_card(BASE_URL)


@app.get("/audio/.well-known/agent.json", tags=["Discovery"])
async def audio_card():
    return audio_agent.agent_card(BASE_URL)


@app.get("/nav/.well-known/agent.json", tags=["Discovery"])
async def nav_card():
    return nav_agent.agent_card(BASE_URL)


# ===========================================================================
# JSON-RPC 2.0 Endpoints  (A2A Protocol)
# ===========================================================================

class RPCBody(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Optional[str] = None


@app.post("/vision/rpc", tags=["A2A"])
async def vision_rpc(body: RPCBody):
    return await vision_agent.dispatch_skill(body.model_dump())


@app.post("/audio/rpc", tags=["A2A"])
async def audio_rpc(body: RPCBody):
    return await audio_agent.dispatch_skill(body.model_dump())


@app.post("/nav/rpc", tags=["A2A"])
async def nav_rpc(body: RPCBody):
    return await nav_agent.dispatch_skill(body.model_dump())


@app.post("/orchestrator/rpc", tags=["A2A"])
async def orchestrator_rpc(body: RPCBody):
    return await orchestrator.dispatch_skill(body.model_dump())


# ===========================================================================
# Convenience REST Endpoints  (used by the frontend)
# ===========================================================================

@app.post("/analyze", tags=["Convenience"])
async def analyze(
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    query: str = Form("Describe my surroundings."),
    senior_mode: bool = Form(False),
    language: str = Form("en"),
    target_lat: Optional[float] = Form(None),
    target_lon: Optional[float] = Form(None),
    current_lat: Optional[float] = Form(None),
    current_lon: Optional[float] = Form(None),
):
    """Full pipeline: vision + audio + nav → merged context."""
    image_b64: Optional[str] = None
    audio_b64: Optional[str] = None
    audio_mime = "audio/webm"

    if image:
        raw = await image.read()
        image_b64 = base64.b64encode(raw).decode()
    if audio:
        raw = await audio.read()
        audio_b64 = base64.b64encode(raw).decode()
        audio_mime = audio.content_type or "audio/webm"

    nav_params = None
    if all(v is not None for v in [current_lat, current_lon, target_lat, target_lon]):
        nav_params = {
            "current_lat": current_lat,
            "current_lon": current_lon,
            "target_lat": target_lat,
            "target_lon": target_lon,
        }

    result = await orchestrator.analyze_scene(
        image_b64=image_b64,
        audio_b64=audio_b64,
        audio_mime=audio_mime,
        query=query,
        senior_mode=senior_mode,
        language=language,
        nav_params=nav_params,
    )
    return result


@app.post("/analyze/vision", tags=["Convenience"])
async def analyze_vision(
    image: UploadFile = File(...),
    query: str = Form("Describe my surroundings."),
    senior_mode: bool = Form(False),
    language: str = Form("en"),
    current_lat: Optional[float] = Form(None),
    current_lon: Optional[float] = Form(None),
):
    raw = await image.read()
    image_b64 = base64.b64encode(raw).decode()
    
    # Fetch weather if coordinates are provided
    weather_context = ""
    if current_lat is not None and current_lon is not None:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.open-meteo.com/v1/forecast?latitude={current_lat}&longitude={current_lon}&current=temperature_2m,precipitation,weather_code"
                )
                if resp.status_code == 200:
                    data = resp.json().get("current", {})
                    temp = data.get("temperature_2m", "unknown")
                    precip = data.get("precipitation", 0)
                    weather_context = f"\n[System Context: The user's local temperature is {temp}°C with {precip}mm precipitation. Advise on appropriate clothing/gear like umbrella, warm clothes, or water bottle.]"
        except Exception as e:
            logger.warning(f"Failed to fetch weather: {e}")

    final_query = query + weather_context
    
    result = await vision_agent._skill_analyze_frame(
        image_b64=image_b64, query=final_query, senior_mode=senior_mode, language=language
    )
    return result


@app.post("/analyze/audio", tags=["Convenience"])
async def analyze_audio(
    audio: UploadFile = File(...),
    senior_mode: bool = Form(False),
    language: str = Form("en"),
):
    raw = await audio.read()
    audio_b64 = base64.b64encode(raw).decode()
    result = await audio_agent._skill_monitor_ambient(
        audio_b64=audio_b64,
        mime_type=audio.content_type or "audio/webm",
        senior_mode=senior_mode,
        language=language,
    )
    return result


class HeadingRequest(BaseModel):
    current_lat: float
    current_lon: float
    target_lat: float
    target_lon: float
    obstacle_context: Optional[Dict[str, Any]] = None


@app.post("/nav/heading", tags=["Convenience"])
async def nav_heading(body: HeadingRequest):
    return await nav_agent._skill_calculate_heading(**body.model_dump())


class HapticsRequest(BaseModel):
    maneuver: str = "straight"
    intensity: float = 1.0


@app.post("/nav/haptics", tags=["Convenience"])
async def nav_haptics(body: HapticsRequest):
    return await nav_agent._skill_generate_haptics(**body.model_dump())


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "agents": ["VisionAgent", "AudioAgent", "NavAgent", "Orchestrator"],
        "protocol": "A2A/0.3",
    }
