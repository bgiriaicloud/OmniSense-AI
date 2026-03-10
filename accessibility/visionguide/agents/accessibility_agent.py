import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class AccessibilityAgent(ABC):
    def __init__(self, model_name="gemini-2.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

    def load_prompt(self, prompt_path):
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r') as f:
                return f.read()
        return ""

    @abstractmethod
    def analyze(self, data):
        """Perform analysis on the provided data (image, audio, etc.)"""
        pass
