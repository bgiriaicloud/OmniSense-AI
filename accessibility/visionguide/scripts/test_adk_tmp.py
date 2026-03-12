import asyncio
import os
from google.adk import Agent, Runner
from google.genai import types

os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "mock_key")

agent = Agent(name="TestAgent", model="gemini-2.5-flash", instruction="You are a test agent.")
runner = Runner(agent=agent, app_name="test_app")

new_msg = types.Content(role="user", parts=[types.Part.from_text(text="Hello")])
try:
    events = list(runner.run(user_id="test_user", session_id="test_session", new_message=new_msg))
    print(f"Total events: {len(events)}")
    for e in events:
        print(f"Event type: {type(e).__name__}, Dump: {e.model_dump_json()}")
except Exception as ex:
    print(f"Error: {ex}")
