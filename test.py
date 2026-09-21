import os
import requests
import base64

API_KEY = os.environ.get("XAI_API_KEY")
if not API_KEY:
    raise SystemExit("Set the XAI_API_KEY environment variable")

response = requests.post(
    "https://api.x.ai/v1/tts",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "text": "Hello, this is a test of the Grok Eve voice.",
        "voice_id": "eve",
        "language": "en"
    }
)

print("Status:", response.status_code)
if response.status_code == 200:
    print("Success! Audio length:", len(response.content), "bytes")
else:
    print("Error:", response.text)