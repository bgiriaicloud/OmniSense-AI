from agents.vision_agent import VisionAgent
from agents.audio_agent import AudioAgent
from agents.context_agent import ContextAgent

class AgentRuntime:
    def __init__(self):
        self.vision_agent = VisionAgent()
        self.audio_agent = AudioAgent()
        self.context_agent = ContextAgent()

    def analyze_scene(self, image_data=None, audio_data=None, mime_type="audio/webm", query="Describe my surroundings."):
        results = {}
        
        # Get environmental memory
        context_str = self.context_agent.get_context_for_prompt()

        if image_data:
            # Inject context and user query into vision analysis
            vision_result = self.vision_agent.analyze(image_data, context_string=context_str, query=query)
            
            # Update memory with vision result
            context_result = self.context_agent.analyze(vision_result)
            
            # Add proactive safety tags if memory suggests persistent hazard
            if context_result.get('is_persistent_hazard'):
                vision_result['hazard'] = f"[PERSISTENT] {vision_result['hazard']}"
                vision_result['guidance'] = f"Stay alert! {vision_result['guidance']}"
            
            results['vision'] = vision_result
            
        if audio_data:
            audio_result = self.analyze_audio(audio_data, mime_type=mime_type)
            results['audio'] = audio_result
            
        return results

    def analyze_audio(self, audio_data, mime_type="audio/webm"):
        audio_result = self.audio_agent.analyze(audio_data, mime_type=mime_type)
        # Update memory with audio events
        self.context_agent.analyze({
            "scene": "Audio event", 
            "hazard": audio_result.get('sound_event'), 
            "guidance": audio_result.get('guidance')
        })
        return audio_result
