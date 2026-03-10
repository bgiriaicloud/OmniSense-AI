import requests
import os

def test_api():
    url = "http://localhost:8000/analyze_scene"
    # Create a dummy image for testing if one doesn't exist
    from PIL import Image
    import io

    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    files = {'file': ('test.jpg', img_byte_arr, 'image/jpeg')}
    
    try:
        print(f"Sending request to {url}...")
        response = requests.post(url, files=files)
        print(f"Status Code: {response.status_code}")
        print("Response Content:")
        print(response.json())
        
        if response.status_code == 200:
            print("\n✅ API Verification Successful!")
        else:
            print("\n❌ API Verification Failed.")
    except Exception as e:
        print(f"\n❌ Error connecting to API: {e}")
        print("Make sure the server is running (uvicorn api.main:app --reload)")

if __name__ == "__main__":
    test_api()
