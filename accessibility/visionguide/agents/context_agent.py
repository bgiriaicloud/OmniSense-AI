import json
from .accessibility_agent import AccessibilityAgent

class ContextAgent(AccessibilityAgent):
    """
    Maintains environmental memory to provide proactive safety guidance.
    Now an ADK-powered service for A2A communication.
    """
    def __init__(self):
        super().__init__(
            name="ContextAgent",
            description="Maintains environmental memory and provides historical context via A2A."
        )
        self.memory = []
        self.max_memory = 5
        self.persistent_hazards = []

    def analyze(self, new_observation):
        """
        Updates memory with a new observation and identifies persistent themes.
        """
        # Add new observation to memory
        self.memory.append(new_observation)
        if len(self.memory) > self.max_memory:
            self.memory.pop(0)

        recent_obs = self.memory[-3:]
        hazards = [str(obs.get('hazard', '')).lower() for obs in recent_obs if obs.get('hazard')]
        
        context_summary = "Previous context suggests: "
        if len(self.memory) > 1:
            prev = self.memory[-2]
            recent_scene = prev.get('scene', prev.get('sound_event', 'Unknown'))
            context_summary += f"You were recently near: {recent_scene}."
        else:
            context_summary += "No prior context."

        return {
            "history": self.memory,
            "context_summary": context_summary,
            "is_persistent_hazard": any('car' in h or 'bus' in h for h in hazards)
        }

    def get_context_for_prompt(self):
        """
        A2A Service Method: Returns historical context as a string.
        """
        if not self.memory:
            return "First observation."
        
        recent = self.memory[-1]
        return f"User recently saw: {recent.get('scene', 'Unknown')}. Hazards noted: {recent.get('hazard', 'None')}."
