"""
Convert podcast script to MP3 using Azure Cognitive Services TTS.
Azure free tier: 500K neural chars/month. Neural voices are ~$16/1M chars after that.
A 60-min episode ≈ 45,000 chars → ~11 episodes/month free, then ~$0.72/month.
"""

import os
import re
import math
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

import requests

# Azure TTS config
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "australiaeast")
AZURE_KEY = os.environ["AZURE_SPEECH_KEY"]

# en-GB-LibbyNeural: young female, England accent, supports "chat" style
# Alternatives: en-GB-SoniaNeural (professional), en-GB-AbbiNeural (softer)
VOICE_NAME = "en-GB-LibbyNeural"
SPEECH_RATE = "-5%"
SPEECH_PITCH = "+3%"  # slight lift to keep energy up at slower rate

TTS_ENDPOINT = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
MAX_CHARS_PER_CHUNK = 3500  # Free tier cuts off ~5-6K SSML chars; stay well under


def text_to_ssml(text: str) -> str:
    # Escape XML special chars
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Insert a natural pause at paragraph breaks
    text = re.sub(r'\n{2,}', ' <break time="600ms"/> ', text)
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
    xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-GB">
  <voice name="{VOICE_NAME}">
    <prosody rate="{SPEECH_RATE}" pitch="{SPEECH_PITCH}">
      {text}
    </prosody>
  </voice>
</speak>"""


def split_into_chunks(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    """Split text at sentence boundaries to stay under Azure's char limit."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_chars:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        chunks.append(current.strip())
    return chunks


def synthesize_chunk(text: str, out_path: str, retries: int = 3) -> bool:
    import time
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3",
        "User-Agent": "AIPodcastGenerator/1.0",
    }
    ssml = text_to_ssml(text)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(TTS_ENDPOINT, headers=headers, data=ssml.encode("utf-8"), timeout=90)
            if resp.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                return True
            else:
                print(f"  [ERROR] TTS chunk failed: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"  [WARN] Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(3 * attempt)
    return False


def concatenate_mp3s(chunk_paths: list[str], output_path: str) -> bool:
    """Concatenate MP3 files using ffmpeg."""
    if len(chunk_paths) == 1:
        import shutil
        shutil.copy(chunk_paths[0], output_path)
        return True

    # Write ffmpeg concat list
    list_file = output_path + ".list.txt"
    with open(list_file, "w") as f:
        for p in chunk_paths:
            f.write(f"file '{p}'\n")

    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path],
        capture_output=True, text=True
    )
    Path(list_file).unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"  [ERROR] ffmpeg concat failed: {result.stderr[-500:]}")
        return False
    return True


def generate_audio(script_text: str, output_path: str) -> bool:
    chunks = split_into_chunks(script_text)
    total_chars = sum(len(c) for c in chunks)
    print(f"Generating audio: {len(chunks)} chunks, {total_chars:,} chars total")

    with tempfile.TemporaryDirectory() as tmp:
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            chunk_path = f"{tmp}/chunk_{i:04d}.mp3"
            print(f"  Synthesizing chunk {i+1}/{len(chunks)} ({len(chunk):,} chars)...")
            if not synthesize_chunk(chunk, chunk_path):
                return False
            chunk_paths.append(chunk_path)

        print(f"Concatenating {len(chunk_paths)} audio chunks...")
        success = concatenate_mp3s(chunk_paths, output_path)

    if success:
        size_mb = Path(output_path).stat().st_size / 1_048_576
        print(f"Audio saved: {output_path} ({size_mb:.1f} MB)")
    return success


if __name__ == "__main__":
    import sys
    from datetime import datetime

    script_file = sys.argv[1] if len(sys.argv) > 1 else None
    if not script_file:
        date_tag = datetime.now().strftime("%Y-%m-%d")
        script_file = f"script_{date_tag}.txt"

    with open(script_file, encoding="utf-8") as f:
        script = f.read()

    date_tag = datetime.now().strftime("%Y-%m-%d")
    out_mp3 = f"episode_{date_tag}.mp3"
    generate_audio(script, out_mp3)
