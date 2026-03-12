import sys
import os

try:
    import google.adk as adk
    print("SUCCESS: google.adk imported")
    print(f"Path: {adk.__path__}")
    print(f"Dir: {dir(adk)}")
except ImportError as e:
    print(f"FAILED: {e}")
    # Try to find it manually
    for path in sys.path:
        adk_path = os.path.join(path, "google", "adk")
        if os.path.exists(adk_path):
            print(f"Found adk at: {adk_path}")
            if adk_path not in sys.path:
                print("Adding to sys.path...")
                sys.path.append(adk_path)
