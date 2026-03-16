import json
import io
import os
from .accessibility_agent import AccessibilityAgent
from google.genai import types
import logging

logger = logging.getLogger("omnisense-audio")

class AudioAgent(AccessibilityAgent):
    def __init__(self):
        description = (
            "Environmental sound detection for deaf and hard-of-hearing users. "
            "Identifies sirens, doorbells, bicycle bells, approaching vehicles, "
            "and distant voices, providing urgency-rated alerts."
        )
        self.system_prompt = self.load_prompt("prompts/audio_prompt.txt")
        
        # Reference-specific instruction extension
        adk_instruction = (self.system_prompt if self.system_prompt else description) + """
In live sessions, detect significant environmental sounds and describe 
them clearly in the transcript using brackets.
"""
        
        AccessibilityAgent.__init__(
            self,
            "AudioAgent",
            description,
            os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash"),
            adk_instruction
        )

    def _build_contextual_prompt(self, senior_mode=False, language="en"):
        """
        Helper method to construct the system instructions.
        Centralizes the logic for Senior Mode and Language.
        """
        prompt = self.system_prompt if self.system_prompt else "Describe important sounds in this audio for a visually impaired person."
        
        # Add Senior Citizen / Social instructions
        if senior_mode:
            logger.info(f"[{self.agent_name}] SENIOR CITIZEN MODE ACTIVE for audio analysis.")
            prompt += "\n\nSENIOR CITIZEN MODE ACTIVE: You are a warm, patient, and intellectually engaging companion. Please include:\n1. Small talk or a positive quote to brighten their day.\n2. Reminders for healthy habits: hydration, eating healthy, or light exercise.\n3. A gentle check about their medication if it's high time.\n4. If you hear voices or interesting sounds, engage in small talk or share an intellectual observation about the sound landscape.\nKeep your tone encouraging and friendly."
        
        # Add Language instructions
        if language != "en":
            lang_map = {"fr": "French", "hi": "Hindi", "or": "Odia"}
            target_lang = lang_map.get(language, "English")
            prompt += f"\n\nLANGUAGE REQUIREMENT: Respond in {target_lang}. Ensure all text fields in the output JSON (sound_event, guidance) are in {target_lang}."

        return prompt

    async def analyze(self, audio_data, mime_type=None, senior_mode=False, language="en"):
        """
        Analyzes audio data with support for Senior Citizen Mode and multiple languages using ADK.
        """
        schema_defaults = {
            "sound_event": "Sound event unknown.",
            "urgency": "Normal",
            "guidance": "No guidance provided for this sound."
        }
        
        if not self.agent:
            return {
                "sound_event": "Mock: Distant siren detected.",
                "urgency": "Caution",
                "guidance": "I hear a siren in the distance. Please stay on the sidewalk and be aware of emergency vehicles."
            }

        if not mime_type or mime_type in ["application/octet-stream", ""]:
            mime_type = "audio/webm"

        clean_mime_type = mime_type.split(';')[0].strip()

        # Build standardized prompt
        prompt = self._build_contextual_prompt(senior_mode=senior_mode, language=language)

        try:
            from google.adk import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types
            import uuid
            
            # ADK Best Practice: Update the agent's system instruction and generation config
            # dynamically for this specific run by creating a localized clone.
            run_agent = self.agent.model_copy(update={
                "instruction": prompt,
                "generate_content_config": types.GenerateContentConfig(response_mime_type="application/json")
            })
            
            # Initialize ADK Runner with ephemeral session
            session_service = InMemorySessionService()
            session_id = str(uuid.uuid4())
            await session_service.create_session(app_name="OmniSense", user_id="audio_user", session_id=session_id)
            runner = Runner(agent=run_agent, app_name="OmniSense", session_service=session_service)
            
            new_msg = types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=audio_data, mime_type=clean_mime_type)
                ]
            )
            
            final_text = ""
            async for event in runner.run_async(user_id="audio_user", session_id=session_id, new_message=new_msg):
                if getattr(event, "content", None) and event.content.parts:
                    final_text += "".join(p.text for p in event.content.parts if p.text)
                    
            if not final_text:
                raise ValueError("Response empty or blocked")
            
            # Clean possible markdown formatting
            if "```json" in final_text:
                final_text = final_text.split("```json")[1].split("```")[0].strip()
            elif "```" in final_text:
                final_text = final_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(final_text.strip())
            
            for field, default in schema_defaults.items():
                if field not in data:
                    data[field] = default
            return data
            
        except Exception as e:
            err_msg = str(e)
            logger.error(f"[{self.agent_name}] Generation error: {err_msg}")
            
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                return {**schema_defaults, "urgency": "System is cooling down.", "guidance": "Rate limit reached. Please wait."}
            
            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                return {**schema_defaults, "urgency": "High demand.", "guidance": "System is busy. Please try again later."}

            return {**schema_defaults, "guidance": f"System error: {err_msg}"}
