"""Quick TTS diagnostic — tests short and medium text with current voice settings."""
import os, requests
from generate_audio import text_to_ssml, AZURE_KEY, TTS_ENDPOINT

headers = {
    "Ocp-Apim-Subscription-Key": AZURE_KEY,
    "Content-Type": "application/ssml+xml",
    "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3",
    "User-Agent": "AIPodcastGenerator/1.0",
}

tests = [
    ("short",  "Hello, this is a test of the Azure Text to Speech service."),
    ("medium", "Hello, this is a test. " * 100),   # ~2,400 chars
    ("large",  "Hello, this is a test. " * 300),   # ~7,200 chars
]

for label, text in tests:
    ssml = text_to_ssml(text)
    print(f"Testing {label} ({len(ssml):,} chars SSML)...", end=" ", flush=True)
    try:
        resp = requests.post(TTS_ENDPOINT, headers=headers, data=ssml.encode("utf-8"), timeout=90)
        if resp.status_code == 200:
            with open(f"test_{label}.mp3", "wb") as f:
                f.write(resp.content)
            print(f"OK ({len(resp.content):,} bytes)")
        else:
            print(f"FAILED {resp.status_code}: {resp.text[:300]}")
    except Exception as e:
        print(f"ERROR: {e}")
