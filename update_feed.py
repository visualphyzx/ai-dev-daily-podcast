"""
Upload episode MP3 to GitHub Releases and update the RSS feed XML on GitHub Pages.
The feed.xml lives on the gh-pages branch of your podcast repo.
"""

import os
import re
import json
import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_USER = os.environ["GITHUB_USER"]           # your GitHub username
GITHUB_REPO = os.environ["GITHUB_REPO"]           # e.g. "ai-dev-daily-podcast"
PODCAST_TITLE = "AI Dev Daily"
PODCAST_DESCRIPTION = "Daily 60-minute podcast for developers on the latest AI tools, Claude Code, Codex, LLMs, and best practices."
PODCAST_AUTHOR = "AI Dev Daily"
PODCAST_EMAIL = os.environ.get("PODCAST_EMAIL", "podcast@example.com")
PAGES_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}"

GH_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def upload_mp3_to_release(mp3_path: str, tag: str) -> Optional[str]:
    """Create a GitHub Release for the date and upload the MP3. Returns download URL."""
    repo = f"{GITHUB_USER}/{GITHUB_REPO}"
    size_mb = Path(mp3_path).stat().st_size / 1_048_576

    # Create release
    release_resp = requests.post(
        f"{GH_API}/repos/{repo}/releases",
        headers=HEADERS,
        json={
            "tag_name": tag,
            "name": f"Episode {tag}",
            "body": f"AI Dev Daily episode for {tag} ({size_mb:.1f} MB)",
            "draft": False,
            "prerelease": False,
        },
        timeout=30,
    )
    if release_resp.status_code not in (200, 201):
        # Release may already exist — fetch it
        existing = requests.get(f"{GH_API}/repos/{repo}/releases/tags/{tag}", headers=HEADERS)
        if existing.status_code != 200:
            print(f"[ERROR] Could not create or find release: {release_resp.text[:300]}")
            return None
        release_data = existing.json()
    else:
        release_data = release_resp.json()

    upload_url = release_data["upload_url"].replace("{?name,label}", "")
    asset_name = Path(mp3_path).name

    # Delete existing asset if present (re-run scenario)
    for asset in release_data.get("assets", []):
        if asset["name"] == asset_name:
            requests.delete(f"{GH_API}/repos/{repo}/releases/assets/{asset['id']}", headers=HEADERS)

    # Upload MP3
    with open(mp3_path, "rb") as f:
        mp3_bytes = f.read()

    upload_headers = {**HEADERS, "Content-Type": "audio/mpeg"}
    up_resp = requests.post(
        f"{upload_url}?name={asset_name}",
        headers=upload_headers,
        data=mp3_bytes,
        timeout=300,
    )
    if up_resp.status_code not in (200, 201):
        print(f"[ERROR] Upload failed: {up_resp.text[:300]}")
        return None

    download_url = up_resp.json()["browser_download_url"]
    print(f"Uploaded MP3: {download_url}")
    return download_url


def get_current_feed() -> tuple[str, Optional[str]]:
    """Fetch current feed.xml from gh-pages. Returns (content, sha)."""
    repo = f"{GITHUB_USER}/{GITHUB_REPO}"
    resp = requests.get(
        f"{GH_API}/repos/{repo}/contents/feed.xml",
        headers={**HEADERS, "ref": "gh-pages"},
        timeout=15,
    )
    if resp.status_code == 404:
        return _blank_feed(), None
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def _blank_feed() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{PODCAST_TITLE}</title>
    <link>{PAGES_URL}</link>
    <description>{PODCAST_DESCRIPTION}</description>
    <language>en-us</language>
    <itunes:author>{PODCAST_AUTHOR}</itunes:author>
    <itunes:email>{PODCAST_EMAIL}</itunes:email>
    <itunes:category text="Technology"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
  </channel>
</rss>"""


def _get_audio_duration(mp3_path: str) -> int:
    """Return actual audio duration in seconds using ffprobe."""
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
        capture_output=True, text=True,
    )
    try:
        return int(float(result.stdout.strip()))
    except (ValueError, AttributeError):
        return 0


def add_episode_to_feed(feed_xml: str, date_tag: str, mp3_url: str, mp3_path: str,
                         title: str, description: str) -> str:
    """Insert a new <item> into the RSS feed."""
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    file_size = Path(mp3_path).stat().st_size
    duration_secs = _get_audio_duration(mp3_path)

    new_item = f"""    <item>
      <title>{title}</title>
      <description>{description}</description>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{mp3_url}" length="{file_size}" type="audio/mpeg"/>
      <guid isPermaLink="false">{PAGES_URL}/episodes/{date_tag}</guid>
      <itunes:duration>{duration_secs}</itunes:duration>
      <itunes:episodeType>full</itunes:episodeType>
    </item>"""

    # Insert after <channel> opening tags, before first <item> or before </channel>
    insert_after = "</itunes:type>"
    if insert_after in feed_xml:
        return feed_xml.replace(insert_after, f"{insert_after}\n{new_item}", 1)
    return feed_xml.replace("</channel>", f"{new_item}\n  </channel>")


def push_feed(feed_xml: str, sha: Optional[str]) -> bool:
    """Push updated feed.xml to gh-pages branch."""
    repo = f"{GITHUB_USER}/{GITHUB_REPO}"
    content_b64 = base64.b64encode(feed_xml.encode("utf-8")).decode("ascii")
    payload = {
        "message": f"Add episode {datetime.now().strftime('%Y-%m-%d')}",
        "content": content_b64,
        "branch": "gh-pages",
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(
        f"{GH_API}/repos/{repo}/contents/feed.xml",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        print(f"feed.xml updated on gh-pages")
        return True
    print(f"[ERROR] Feed push failed: {resp.text[:300]}")
    return False


def publish_episode(mp3_path: str, title: str, description: str, date_tag: Optional[str] = None) -> bool:
    if date_tag is None:
        date_tag = datetime.now().strftime("%Y-%m-%d")

    print(f"Publishing episode {date_tag}...")

    mp3_url = upload_mp3_to_release(mp3_path, date_tag)
    if not mp3_url:
        return False

    feed_xml, sha = get_current_feed()
    updated_feed = add_episode_to_feed(feed_xml, date_tag, mp3_url, mp3_path, title, description)
    return push_feed(updated_feed, sha)


if __name__ == "__main__":
    import sys
    from datetime import datetime

    date_tag = datetime.now().strftime("%Y-%m-%d")
    mp3_file = f"episode_{date_tag}.mp3"
    script_file = f"script_{date_tag}.txt"

    with open(script_file, encoding="utf-8") as f:
        script = f.read()

    # Use first 200 chars of script as description
    description = script[:200].replace("<", "&lt;").replace(">", "&gt;") + "..."
    title = f"AI Dev Daily — {date_tag}"

    publish_episode(mp3_file, title, description, date_tag)
