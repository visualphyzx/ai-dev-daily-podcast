"""
Main daily pipeline orchestrator.
Run this every morning to produce and publish a new podcast episode.

Usage:
    python run_daily.py
    python run_daily.py --provider deepseek
    python run_daily.py --provider ollama --model llama3.1:70b
    python run_daily.py --skip-upload   # generate locally, don't publish
    python run_daily.py --script-only   # only collect news + generate script
    python run_daily.py --list-providers
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

from collect_news import collect_all
from generate_script import generate_script, list_providers, PROVIDERS
from generate_audio import generate_audio
from update_feed import publish_episode


def main():
    parser = argparse.ArgumentParser(description="AI Dev Daily podcast pipeline")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "claude"),
                        choices=list(PROVIDERS.keys()),
                        help="LLM provider for script generation (default: claude)")
    parser.add_argument("--model", help="Override the default model for the chosen provider")
    parser.add_argument("--list-providers", action="store_true", help="List available LLM providers and exit")
    parser.add_argument("--skip-upload", action="store_true", help="Generate files locally, skip GitHub upload")
    parser.add_argument("--script-only", action="store_true", help="Only collect news and generate script")
    parser.add_argument("--date", help="Override date tag (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.list_providers:
        list_providers()
        return

    date_tag = args.date or datetime.now().strftime("%Y-%m-%d")
    date_str = datetime.strptime(date_tag, "%Y-%m-%d").strftime("%A, %B %d, %Y")

    cache_file = f"news_{date_tag}.json"
    script_file = f"script_{date_tag}.txt"
    mp3_file = f"episode_{date_tag}.mp3"

    # Step 1: Collect news
    if not Path(cache_file).exists():
        print("=" * 60)
        print("STEP 1: Collecting news")
        print("=" * 60)
        import json
        articles = collect_all()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(articles)} articles to {cache_file}\n")
    else:
        import json
        with open(cache_file, encoding="utf-8") as f:
            articles = json.load(f)
        print(f"Using cached news: {len(articles)} articles from {cache_file}\n")

    # Step 2: Generate script
    if not Path(script_file).exists():
        print("=" * 60)
        print("STEP 2: Generating podcast script")
        print("=" * 60)
        script = generate_script(articles, date_str, provider=args.provider, model=args.model)
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)
        print(f"Script saved to {script_file}\n")
    else:
        with open(script_file, encoding="utf-8") as f:
            script = f.read()
        print(f"Using cached script: {script_file} ({len(script.split()):,} words)\n")

    if args.script_only:
        print("--script-only flag set, stopping here.")
        return

    # Step 3: Generate audio
    if not Path(mp3_file).exists():
        print("=" * 60)
        print("STEP 3: Generating audio (Azure TTS)")
        print("=" * 60)
        success = generate_audio(script, mp3_file)
        if not success:
            print("[ERROR] Audio generation failed")
            sys.exit(1)
        print()
    else:
        size_mb = Path(mp3_file).stat().st_size / 1_048_576
        print(f"Using cached audio: {mp3_file} ({size_mb:.1f} MB)\n")

    if args.skip_upload:
        print(f"--skip-upload flag set. Files ready locally:")
        print(f"  Script: {script_file}")
        print(f"  Audio:  {mp3_file}")
        return

    # Step 4: Publish to GitHub
    print("=" * 60)
    print("STEP 4: Publishing to GitHub Pages RSS feed")
    print("=" * 60)
    title = f"AI Dev Daily — {date_str}"
    description = script[:200].replace("<", "&lt;").replace(">", "&gt;") + "..."
    success = publish_episode(mp3_file, title, description, date_tag)
    if success:
        print(f"\nEpisode published! RSS feed updated.")
        print(f"Feed URL: https://{os.environ.get('GITHUB_USER', 'YOU')}.github.io/{os.environ.get('GITHUB_REPO', 'REPO')}/feed.xml")
    else:
        print("[ERROR] Publishing failed — check logs above")
        sys.exit(1)


if __name__ == "__main__":
    main()
