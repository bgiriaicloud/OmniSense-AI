import os
import json
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from google import genai
from google.adk import Agent
import logging

logger = logging.getLogger("omnisense-agent")
load_dotenv(override=True)

class AccessibilityAgent(ABC):
    def __init__(self, name, description, model_id=None, instruction=None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_id = model_id or os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")
        logger.info(f"[{name}] Initializing with API Key: {self.api_key[:8]}... and Model: {self.model_id}")
        
        if self.api_key:
            logger.info(f"[{name}] API Key found. Initializing live Gemini client.")
            self.client = genai.Client(api_key=self.api_key)
            self.agent_name = name
            self.description = description
            
            # ADK Agent definition - Using Agent (LlmAgent) directly
            self.agent = Agent(
                name=self.agent_name,
                description=self.description,
                model=self.model_id,
                instruction=instruction or self.description # Default instruction
            )
        else:
            logger.warning(f"[{name}] GEMINI_API_KEY NOT FOUND. Running in MOCK MODE.")
            self.client = None
            self.agent = None

    def get_adk_agent(self) -> Agent:
        """Returns the ADK Agent instance."""
        return self.agent

    def load_prompt(self, prompt_path):
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r') as f:
                return f.read()
        return ""

    async def _generate_json(self, prompt, parts, schema_defaults, senior_mode=False):
        """
        Standardized method for generating and parsing JSON content from Gemini.
        Includes error handling for rate limits and busy systems.
        """
        try:
            # Use generate_content through the client
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt] + parts,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            if not response.text:
                raise ValueError("Empty response from AI")

            data = json.loads(response.text.strip())
            
            # Enforce schema with defaults
            for field, default in schema_defaults.items():
                if field not in data:
                    data[field] = default
            return data

        except Exception as e:
            err_msg = str(e)
            logger.error(f"[{self.agent_name}] Generation error: {err_msg}")
            
            # Standardized Resilience: Use the same signatures as VisionAgent
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                return {**schema_defaults, "hazard": "System is cooling down.", "guidance": "Rate limit reached. Please wait."}
            
            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                return {**schema_defaults, "hazard": "High demand.", "guidance": "System is busy. Please try again later."}

            return {**schema_defaults, "guidance": f"System error: {err_msg}"}

    @abstractmethod
    def analyze(self, data, **kwargs):
        """Perform analysis on the provided data."""
        pass
