import json
import logging
from typing import Dict, Any

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory import InMemorySessionService
from google.genai import types

try:
    # Attempt to import generic base class from a hypothetical shared location
    from base_agent import AccessibilityAgent
except ImportError:
    # Mock base class if missing
    class AccessibilityAgent:
        def __init__(self, agent: Agent):
            self.agent = agent

class AudioAgent(AccessibilityAgent):
    def __init__(self):
        # 1. Core Agent Definition
        root_agent = Agent(
            model='gemini-2.5-flash',
            name="AudioAgent",
            description="Environmental sound detection for deaf and hard-of-hearing users. Identifies sirens, doorbells, bicycle bells, approaching vehicles, and distant voices, providing urgency-rated alerts.",
            instruction='''You are an expert Audio Accessibility Assistant for users who are deaf or hard of hearing. Your goal is to detect and identify significant environmental sounds from the provided audio, including those from a distance. Pay extra attention to: Doorbells, Baby crying, Sirens, Bicycle bells, Distant voices, and Approaching vehicles.

Return a JSON object with:
- "sound_event": Concise identification (e.g., "Distant siren").
- "urgency": "Critical", "Caution", or "Safe".
- "guidance": Actionable advice (e.g., "emergency vehicle nearby, stay clear").
For live sessions: Detect sounds and describe them in the transcript using brackets.'''
        )
        # 2. Initialization: Register the agent with the model
        super().__init__(root_agent)

    # 3. Execution Logic
    async def analyze(self, audio_data: bytes, mime_type: str, senior_mode: bool, language: str) -> Dict[str, Any]:
        """
        Analyzes audio data for significant environmental sounds.
        """
        # 4. Contextual Logic
        dynamic_prompt = self.agent.instruction
        
        if senior_mode:
            dynamic_prompt += (
                "\n\nSenior Mode Enabled: Please use a warm, encouraging tone. "
                "Include a short daily quote and a wellness reminder "
                "(e.g., for hydration or medication) in the guidance field."
            )
            
        if language and language.lower() != "english":
            dynamic_prompt += f"\n\nLanguage Translation: Translate all text fields in the returned JSON object into {language}."

        # 2. Dynamic Context (ADK model_copy)
        # Create a thread-safe, request-specific clone of the agent
        request_agent = self.agent.model_copy(update={"instruction": dynamic_prompt})

        # 3. ADK Runner
        runner = Runner(agent=request_agent, session_service=InMemorySessionService())
        
        # Input Handling
        try:
            audio_part = types.Part.from_bytes(data=audio_data, mime_type=mime_type)
        except AttributeError:
            # Fallback for different GenAI SDK versions
            audio_part = types.Part(
                inline_data=types.Blob(data=audio_data, mime_type=mime_type)
            )

        user_content = types.Content(
            role="user",
            parts=[audio_part]
        )
        
        # 5. Error Handling & Resilience
        try:
            # Response Processing
            response_text = ""
            async for chunk in runner.run_async(user_content):
                if hasattr(chunk, 'text') and chunk.text:
                    response_text += chunk.text
            
            # Clean up markdown backticks for JSON parsing
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
                
            clean_text = clean_text.strip()
            
            result = json.loads(clean_text)
            
            # Schema defaults to ensure UI never crashes on missing fields
            return {
                "sound_event": result.get("sound_event", "Unknown sound event"),
                "urgency": result.get("urgency", "Safe"),
                "guidance": result.get("guidance", "No specific guidance available.")
            }
            
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON response: {response_text}")
            return {
                "sound_event": "Analysis Complete (Format Error)",
                "urgency": "Caution",
                "guidance": "The sound analysis was completed, but the response format was invalid."
            }
        except Exception as e:
            error_str = str(e).lower()
            # Catch 429 (Resource Exhausted) and 503 (Unavailable) errors
            if "429" in error_str or "resource exhausted" in error_str:
                return {
                    "sound_event": "System Busy",
                    "urgency": "Safe",
                    "guidance": "Our system is currently experiencing high demand. Please try again in a few moments."
                }
            elif "503" in error_str or "unavailable" in error_str:
                return {
                    "sound_event": "System Unavailable",
                    "urgency": "Safe",
                    "guidance": "The sound analysis service is currently unavailable or cooling down. Please check back later."
                }
            else:
                logging.exception("Unexpected error during audio analysis")
                return {
                    "sound_event": "System Error",
                    "urgency": "Caution",
                    "guidance": "An unexpected error occurred during audio analysis. Please try again."
                }