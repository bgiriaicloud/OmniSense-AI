from agents.vision_agent import VisionAgent
from agents.audio_agent import AudioAgent
from agents.context_agent import ContextAgent

class AgentRuntime:
    def __init__(self):
        self.vision_agent = VisionAgent()
        self.audio_agent = AudioAgent()
        self.context_agent = ContextAgent()

    async def analyze_scene(self, image_data=None, audio_data=None, mime_type="audio/webm", query="Describe my surroundings.", senior_mode=False, language="en"):
        results = {}
        
        if image_data:
            vision_result = await self.vision_agent.analyze(
                image_data, 
                context_agent=self.context_agent, 
                query=query,
                senior_mode=senior_mode,
                language=language
            )
            
            # Update memory service
            context_result = self.context_agent.analyze(vision_result)
            
            # Post-process with historical insights
            if context_result.get('is_persistent_hazard'):
                vision_result['hazard'] = f"[PERSISTENT] {vision_result['hazard']}"
                vision_result['guidance'] = f"Stay alert! {vision_result['guidance']}"
            
            results['vision'] = vision_result
            
        if audio_data:
            audio_result = await self.analyze_audio(audio_data, mime_type=mime_type, senior_mode=senior_mode, language=language)
            results['audio'] = audio_result
            
        return results

    async def analyze_audio(self, audio_data, mime_type="audio/webm", senior_mode=False, language="en"):
        audio_result = await self.audio_agent.analyze(audio_data, mime_type=mime_type, senior_mode=senior_mode, language=language)
        # Update memory with audio events
        self.context_agent.analyze({
            "scene": "Audio event", 
            "hazard": audio_result.get('sound_event'), 
            "guidance": audio_result.get('guidance')
        })
        return audio_result

    def get_adk_agents(self):
        """Returns a list of all ADK agents managed by this runtime."""
        return [
            self.vision_agent.get_adk_agent(),
            self.audio_agent.get_adk_agent(),
            self.context_agent.get_adk_agent()
        ]
