import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_discovery():
    print("Testing A2A Discovery Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/.well-known/agent.json")
        response.raise_for_status()
        card = response.json()
        print(f"SUCCESS: Received Agent Card: {json.dumps(card, indent=2)}")
        return True
    except Exception as e:
        print(f"FAILED: Discovery endpoint error: {e}")
        return False

def test_execution():
    print("\nTesting A2A Execution Endpoint...")
    payload = {
        "user_id": "test_user",
        "session_id": "test_session",
        "new_message": "Hello VisionAgent, what can you do?"
    }
    try:
        response = requests.post(f"{BASE_URL}/run", json=payload, stream=True)
        response.raise_for_status()
        print("SUCCESS: Connection established. Streaming events:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    event = json.loads(decoded_line[6:])
                    print(f"Event: {json.dumps(event, indent=2)}")
        return True
    except Exception as e:
        print(f"FAILED: Execution endpoint error: {e}")
        return False

if __name__ == "__main__":
    discovery_ok = test_discovery()
    execution_ok = test_execution()
    
    if discovery_ok and execution_ok:
        print("\nALL VERIFICATIONS PASSED")
        sys.exit(0)
    else:
        print("\nVERIFICATIONS FAILED")
        sys.exit(1)
