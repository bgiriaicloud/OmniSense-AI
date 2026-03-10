import json
from .accessibility_agent import AccessibilityAgent

class VisionAgent(AccessibilityAgent):
    def __init__(self):
        super().__init__()
        self.system_prompt_template = self.load_prompt("prompts/vision_prompt.txt")

    def analyze(self, image_data, context_string="First observation.", query="Describe my surroundings."):
        """
        Analyzes an image and returns structured guidance tailored to the user's voice query.
        """
        if not self.model:
            return {
                "scene": "Mock: A bright, modern hallway.",
                "hazard": "Mock: None detected.",
                "guidance": "AI model not configured.",
                "safety_level": "Safe"
            }

        # Inject user query and context into the prompt
        prompt = self.system_prompt_template.replace("{{USER_QUERY}}", query) if self.system_prompt_template else f"Analyze this image. User query: {query}"
        if context_string and context_string != "First observation.":
            prompt = f"Context from previous observation: {context_string}\n\n{prompt}"

        try:
            response = self.model.generate_content([prompt, image_data])

            if not response.candidates:
                print(f"VisionAgent: No candidates in response. Prompt Feedback: {response.prompt_feedback}")
                raise ValueError("Response blocked or empty")

            text = response.text.strip()

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)
        except Exception as e:
            print(f"Error in VisionAgent: {type(e).__name__}: {e}")
            return {
                "scene": "Error analyzing image",
                "hazard": "Unknown",
                "guidance": "I'm having trouble with my vision system. Please be careful.",
                "safety_level": "Critical"
            }
