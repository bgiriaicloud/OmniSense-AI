from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image
import io
import logging
import os
from orchestrator.agent_runtime import AgentRuntime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from google.adk import Runner, Agent
from google.adk.agents.run_config import RunConfig
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
import json
import uuid
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("omnisense-api")

# Pydantic Models for Response Validation
class VisionResponse(BaseModel):
    scene: str
    hazard: str
    guidance: str
    safety_level: str

class AudioResponse(BaseModel):
    sound_event: str
    urgency: str
    guidance: str

class HealthStatus(BaseModel):
    status: str
    version: str

app = FastAPI(
    title="OmniSense API",
    description="Advanced Accessibility Orchestrator powered by Gemini",
    version="1.1.0"
)

# Global dictionary to store runners
runners: Dict[str, Runner] = {}

# Initialize Orchestrator
try:
    runtime = AgentRuntime()
    # Initialize Session Service for Runners
    session_service = InMemorySessionService()
    # Initialize ADK Runners for each agent
    for agent in runtime.get_adk_agents():
        runners[agent.name] = Runner(
            agent=agent,
            app_name="OmniSense",
            session_service=session_service
        )
    logger.info(f"Orchestrator runtime and {len(runners)} ADK runners initialized with InMemorySessionService.")
except Exception as e:
    logger.critical(f"Failed to initialize AgentRuntime or Runners: {e}")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )

# Mount static files and React build
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    @app.get("/", include_in_schema=False)
    async def read_index():
        return FileResponse("frontend/dist/index.html")
else:
    # Fallback to legacy mobile UI
    app.mount("/static", StaticFiles(directory="mobile"), name="static")
    @app.get("/", include_in_schema=False)
    async def read_index():
        return FileResponse("mobile/index.html")

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """System health check endpoint."""
    return HealthStatus(status="healthy", version="1.1.0")

# A2A Protocol Discovery Endpoint
@app.get("/.well-known/agent.json")
async def get_agent_card():
    """A2A discovery endpoint returning the agent card."""
    logger.info(f"A2A Discovery request received. Available runners: {list(runners.keys())}")
    
    # Try to get VisionAgent, or fallback to the first available runner
    agent_runner = runners.get("VisionAgent") or (next(iter(runners.values())) if runners else None)
    
    if not agent_runner:
        logger.error("No runners initialized for A2A discovery")
        raise HTTPException(status_code=500, detail="No agents initialized for A2A discovery")
        
    primary_agent = agent_runner.agent
    return {
        "name": primary_agent.name,
        "description": primary_agent.description,
        "developer": getattr(primary_agent, 'developer', 'OmniSense Team'),
        "help": getattr(primary_agent, 'help', primary_agent.description),
        "version": "1.1.0",
        "endpoints": {
            "run": "/run"
        }
    }

# A2A Protocol Execution Endpoint
class A2ARunRequest(BaseModel):
    user_id: str = Field(..., alias="user_id")
    session_id: str = Field(..., alias="session_id")
    new_message: Optional[str] = Field(None, alias="new_message")
    invocation_id: Optional[str] = Field(None, alias="invocation_id")
    state_delta: Optional[Dict[str, Any]] = Field(None, alias="state_delta")

@app.post("/run")
async def run_agent_a2a(req: A2ARunRequest):
    """A2A execution endpoint."""
    # Route to VisionAgent by default for A2A
    runner = runners.get("VisionAgent")
    if not runner or not runner.agent:
        raise HTTPException(status_code=500, detail="VisionAgent runner not initialized")

    async def event_generator():
        # Ensure session service exists (A2A support)
        if 'session_service' not in globals():
            yield "data: {\"error\": \"Session service not initialized\"}\n\n"
            return

        session = await session_service.get_session(
            app_name="OmniSense",
            user_id=req.user_id,
            session_id=req.session_id
        )
        if not session:
            logger.info(f"Creating new session for user {req.user_id}, session {req.session_id}")
            await session_service.create_session(
                app_name="OmniSense",
                user_id=req.user_id,
                session_id=req.session_id
            )

        # Runner.run_async expects a Content object for new_message
        new_msg = None
        if req.new_message:
            new_msg = genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=req.new_message)]
            )

        if not runner:
            yield "data: {\"error\": \"Runner lost\"}\n\n"
            return

        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=req.session_id,
            new_message=new_msg,
            invocation_id=req.invocation_id,
            state_delta=req.state_delta
        ):
            yield f"data: {event.model_dump_json(exclude_none=True, by_alias=True)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/analyze_scene", response_model=VisionResponse)
async def analyze_scene(
    file: UploadFile = File(...), 
    query: str = Form("Describe my surroundings."),
    senior_mode: str = Form("false"),
    language: str = Form("en")
):
    # Robust boolean parsing for Form data
    is_senior = senior_mode.lower() == "true"
    logger.info(f"Received vision request: {file.filename}, query: '{query}', senior: {is_senior}, lang: {language}")
    
    if not file.content_type.startswith("image/"):
        logger.warning(f"Invalid content type for vision: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        contents = await file.read()
        
        result = await runtime.analyze_scene(
            image_data=contents, 
            query=query, 
            senior_mode=is_senior, 
            language=language
        )
        result_vision = result.get('vision', {})
        logger.info(f"Final Vision feedback to client: {result_vision.get('scene')} | {result_vision.get('guidance')}")
        return result_vision
        
    except Exception as e:
        logger.error(f"Error in vision analysis: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_audio", response_model=AudioResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    senior_mode: str = Form("false"),
    language: str = Form("en")
):
    is_senior = senior_mode.lower() == "true"
    logger.info(f"Received audio request: {file.filename}, content_type: {file.content_type}, senior: {is_senior}, lang: {language}")
    
    try:
        audio_bytes = await file.read()
        
        result = await runtime.analyze_scene(
            audio_data=audio_bytes, 
            mime_type=file.content_type,
            senior_mode=is_senior,
            language=language
        )
        logger.info(f"Agent audio analysis complete. Result keys: {list(result.keys())}")
        return result['audio']
        
    except Exception as e:
        logger.error(f"Error in audio analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("New WebSocket connection for live accessibility stream.")
    
    # Configuration from client (can be passed via query params or first message)
    # Defaulting to senior_mode=True as per user example
    senior_mode = True 
    language = "en"
    
    try:
        # 1. Start Gemini Live Session
        
        # Establish direct Live API connection using the agent's client
        session_model = getattr(runtime.vision_agent, 'live_model_id', None) or runtime.vision_agent.model_id
        client = runtime.vision_agent.client
        
        # Configuration for the Live Session
        config = {
            "generation_config": {
                "response_modalities": ["AUDIO"]
            },
            "system_instruction": runtime.vision_agent.live_prompt
        }
        
        async with client.aio.live.connect(model=session_model, config=config) as session:
            logger.info("Gemini Live Session connected.")

            async def send_to_gemini():
                try:
                    while True:
                        # Receive binary chunk from frontend
                        data = await websocket.receive_bytes()
                        if not data: continue
                        
                        # Protocol: First byte 0x01 = Video, 0x02 = Audio
                        msg_type = data[0]
                        payload = data[1:]
                        
                        if msg_type == 0x01:
                            # Forward Video to Gemini
                            await session.send_realtime_input(media_chunks=[
                                genai_types.LiveClientRealtimeInputBlob(data=payload, mime_type="image/jpeg")
                            ])
                        elif msg_type == 0x02:
                            # Forward Audio to Gemini
                            await session.send_realtime_input(media_chunks=[
                                genai_types.LiveClientRealtimeInputBlob(data=payload, mime_type="audio/webm")
                            ])
                except WebSocketDisconnect:
                    logger.info("Frontend WebSocket disconnected.")
                    raise
                except Exception as e:
                    logger.error(f"Error sending to Gemini: {e}")

            async def receive_from_gemini():
                try:
                    async for response in session.receive():
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.inline_data:
                                    # Forward raw PCM audio to frontend
                                    await websocket.send_bytes(part.inline_data.data)
                except Exception as e:
                    logger.error(f"Error receiving from Gemini: {e}")

            # Run both tasks concurrently
            await asyncio.gather(send_to_gemini(), receive_from_gemini())

    except WebSocketDisconnect:
        logger.info("Live WebSocket session ended.")
    except Exception as e:
        logger.error(f"Fatal error in live WebSocket: {e}")
    finally:
        logger.info("Cleaning up Live WebSocket session.")
