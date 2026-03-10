import json
from .accessibility_agent import AccessibilityAgent

class AudioAgent(AccessibilityAgent):
    def __init__(self):
        super().__init__()
        self.system_prompt = self.load_prompt("prompts/audio_prompt.txt")

    def analyze(self, audio_data, mime_type=None):
        """
        Analyzes audio data with robust MIME type handling.
        """
        if not self.model:
            return {
                "sound_event": "Mock: Distant siren detected.",
                "urgency": "Caution",
                "guidance": "I hear a siren in the distance. Please stay on the sidewalk and be aware of emergency vehicles."
            }

        # Robust MIME type logic
        if not mime_type or mime_type in ["application/octet-stream", ""]:
            mime_type = "audio/webm"

        # Strip parameters if any (e.g., audio/webm;codecs=opus -> audio/webm)
        clean_mime_type = mime_type.split(';')[0].strip()

        # Prompt for audio analysis
        prompt = self.system_prompt if self.system_prompt else "Describe important sounds in this audio for a visually impaired person."

        try:
            audio_part = {
                "mime_type": clean_mime_type,
                "data": audio_data
            }
            response = self.model.generate_content([prompt, audio_part])

            if not response.candidates:
                print(f"AudioAgent: No candidates in response. Prompt Feedback: {response.prompt_feedback}")
                raise ValueError("Response blocked or empty")

            text = response.text.strip()

            # Simple JSON extraction
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()

            return json.loads(text)
        except Exception as e:
            print(f"Error in AudioAgent: {type(e).__name__}: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                try:
                    print(f"Raw AI response snippet: {response.text[:100]}")
                except:
                    pass
            return {
                "sound_event": "Error analyzing audio",
                "urgency": "Unknown",
                "guidance": "I'm having trouble hearing the environment. Please rely on your other senses for a moment."
            }
