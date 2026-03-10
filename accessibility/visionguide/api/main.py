from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image
import io
import logging
import os
from orchestrator.agent_runtime import AgentRuntime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("omnisense-api")

app = FastAPI(title="OmniSense API")

# Initialize Orchestrator
runtime = AgentRuntime()

# Mount static files
app.mount("/static", StaticFiles(directory="mobile"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("mobile/index.html")

@app.post("/analyze_scene")
async def analyze_scene(file: UploadFile = File(...), query: str = Form("Describe my surroundings.")):
    logger.info(f"Received vision analysis request: {file.filename}, query: '{query}'")
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Using the orchestrator with the voice query
        result = runtime.analyze_scene(image_data=image, query=query)
        return result['vision']
        
    except Exception as e:
        logger.error(f"Error in vision analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_audio")
async def analyze_audio(file: UploadFile = File(...)):
    logger.info(f"Received audio analysis request: {file.filename}")
    
    # Simple check for audio (Gemini supports many formats)
    try:
        audio_bytes = await file.read()
        
        # Using the orchestrator with detected mime_type
        result = runtime.analyze_scene(audio_data=audio_bytes, mime_type=file.content_type)
        return result['audio']
        
    except Exception as e:
        logger.error(f"Error in audio analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
