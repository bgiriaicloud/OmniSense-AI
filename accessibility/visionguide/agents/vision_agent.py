import json
import asyncio
import logging
import os
from .accessibility_agent import AccessibilityAgent
from google.genai import types

logger = logging.getLogger("omnisense-vision")

class VisionAgent(AccessibilityAgent):
    def __init__(self):
        description = (
            "Real-time camera frame analysis. Identifies scenes, obstacles, hazards, "
            "and navigation cues for visually impaired users using spatial language."
        )
        self.static_prompt = self.load_prompt("prompts/vision_prompt.txt")
        self.live_prompt = self.load_prompt("prompts/live_vision_prompt.txt")
        
        # Reference-specific instruction extension
        adk_instruction = (self.static_prompt if self.static_prompt else description) + """
For continuous live sessions, your goal is to be a calm, caring navigation 
companion. Report scene changes, hazards, and guidance in clear speech.
"""
        
        # Support separate Live model for Native Audio Preview
        live_model = os.getenv("GEMINI_LIVE_MODEL_ID")
        self.live_model_id = live_model if live_model else None
        
        AccessibilityAgent.__init__(
            self,
            "VisionAgent",
            description,
            os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash"),
            adk_instruction
        )

    def _build_contextual_prompt(self, context_agent=None, query=None, senior_mode=False, language="en", is_live=False):
        """
        Helper method to construct the system instructions.
        Centralizes the logic for Senior Mode, Language, and Memory.
        """
        # A2A: Retrieve historical context
        context_string = "First observation."
        if context_agent:
            context_string = context_agent.get_context_for_prompt()

        # Handle the base prompt
        if is_live:
            prompt = self.live_prompt if self.live_prompt else "You are a real-time vision assistant. Analyze the video and audio stream."
        else:
            prompt = self.static_prompt.replace("{{USER_QUERY}}", query) if self.static_prompt else f"Analyze this image. User query: {query}"
        
        # Add Senior Citizen / Social instructions
        if senior_mode:
            logger.info(f"[{self.agent_name}] SENIOR CITIZEN MODE ACTIVE.")
            prompt += "\n\nSENIOR CITIZEN MODE ACTIVE: You are a warm, patient, and intellectually engaging companion. Please include:\n1. Small talk or a positive quote to brighten their day.\n2. Reminders for healthy habits: hydration, eating healthy, or light exercise.\n3. A gentle check about their medication if it's high time.\n4. Intellectual conversation about the visual scene (share historical facts or interesting observations).\nKeep your tone encouraging and friendly."
        
        # Add Language instructions
        if language != "en":
            lang_map = {"fr": "French", "hi": "Hindi", "or": "Odia"}
            target_lang = lang_map.get(language, "English")
            if is_live:
                prompt += f"\n\nLANGUAGE REQUIREMENT: You must speak and respond exclusively in {target_lang}."
            else:
                prompt += f"\n\nLANGUAGE REQUIREMENT: Respond in {target_lang}. Ensure all text fields in the output JSON (scene, hazard, guidance) are in {target_lang}."

        if context_string and context_string != "First observation.":
            prompt = f"Context from previous observation: {context_string}\n\n{prompt}"

        # IMPORTANT: Ensure the specific user query is prioritized while still performing environment analysis.
        if not is_live and query:
            prompt += f"\n\nACTUAL USER QUESTION: {query}\nPlease answer this question directly in the 'scene' field of your JSON, then continue with the rest of the environmental analysis as per your system instructions."

        return prompt

    # ==========================================
    # 1. PRESERVED: Single-shot JSON Analysis
    # ==========================================
    async def analyze(self, image_data, context_agent=None, query="Describe my surroundings.", senior_mode=False, language="en"):
        """
        Analyzes a single image and returns a structured JSON dictionary.
        """
        if not self.client:
            return {
                "scene": "Mock: A bright, modern hallway.",
                "hazard": "Mock: None detected.",
                "guidance": "AI model not configured.",
                "safety_level": "Safe"
            }

        prompt = self._build_contextual_prompt(context_agent, query, senior_mode, language, is_live=False)
        schema_defaults = {
            "scene": "Scene description unavailable.",
            "hazard": "No hazard information.",
            "guidance": "No guidance provided.",
            "safety_level": "Unknown"
        }

        # Wrap image data explicitly
        parts = [types.Part.from_bytes(data=image_data, mime_type="image/jpeg")]
        
        # Use standardized generation helper
        return await self._generate_json(prompt, parts, schema_defaults, senior_mode)

    # ==========================================
    # 2. NEW: Real-time Multimodal Live Stream
    # ==========================================
    async def start_live_session(self, context_agent=None, senior_mode=False, language="en"):
        """
        Initiates a real-time WebSocket connection using the Multimodal Live API.
        Returns the active session object so your main application loop can send/receive frames.
        """
        if not self.client:
            raise ValueError("Gemini client not initialized.")

        # Build instructions for the live session
        system_instruction = self._build_contextual_prompt(
            context_agent, query=None, senior_mode=senior_mode, language=language, is_live=True
        )

        config = types.LiveConnectConfig(
            # Voice assistants don't return JSON, they speak!
            response_modalities=[types.LiveResponseModality.AUDIO], 
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=system_instruction)]
            )
        )

        logger.info(f"Starting Live Vision Session with model: {self.model_id}")
        
        # We return the context manager so the calling function can manage the stream loop
        return self.client.aio.live.connect(model=self.model_id, config=config)
