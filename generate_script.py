"""
Generate a 60-minute podcast script using a configurable LLM provider.

Supported providers (set via --provider flag or LLM_PROVIDER env var):
  claude    — Anthropic Claude (default)
  openai    — OpenAI GPT
  deepseek  — DeepSeek (OpenAI-compatible API)
  gemini    — Google Gemini
  ollama    — Local Ollama instance (free, no API key)

Required env vars per provider:
  claude:   ANTHROPIC_API_KEY
  openai:   OPENAI_API_KEY
  deepseek: DEEPSEEK_API_KEY
  gemini:   GEMINI_API_KEY
  ollama:   OLLAMA_BASE_URL (default: http://localhost:11434)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

PODCAST_NAME = "AI Dev Daily"
HOST_NAME = "Alex"  # change to your preferred host name

SCRIPT_PROMPT = """You are a podcast script writer for "{podcast_name}", a daily 60-minute show
for software developers about the latest in AI tools, Claude Code, OpenAI Codex, LLMs,
developer workflows, and AI best practices.

Today is {date}. Here are today's collected news items and articles:

<news>
{news_json}
</news>

Write a complete, natural-sounding 60-minute podcast script. Requirements:

1. **Length**: Approximately 8,500 words (60 min at ~140 wpm speaking pace)
2. **Host**: Single host named {host_name}, conversational and enthusiastic but not over-the-top
3. **Structure**:
   - Intro (2 min): Welcome, today's date, quick preview of top stories
   - Segment 1 - "Big News" (15 min): Top 2-3 major AI announcements/releases
   - Segment 2 - "Developer Tools & Workflows" (15 min): Claude Code, Codex, IDEs, coding tools
   - Segment 3 - "Deep Dive" (12 min): Pick the most interesting story for detailed analysis
   - Segment 4 - "Community & Open Source" (10 min): GitHub trending, community news
   - Segment 5 - "Quick Takes" (4 min): Rapid-fire 3-4 smaller items
   - Outro (2 min): Summary, what to watch for tomorrow, sign-off
4. **Style**:
   - Written for audio — no bullet points, no markdown, just flowing prose
   - Natural transitions between topics
   - Occasionally say things like "if you're following along on your watch" or "whether you're running or cycling"
   - Include concrete examples, code snippet descriptions (describe what the code does, don't recite it)
   - Analysis and opinion, not just summaries
5. **Focus on**: Practical implications for developers, how-to insights, comparisons between tools

Write ONLY the script text — no stage directions, no [PAUSE] markers, no brackets.
The output will be fed directly to text-to-speech.

Begin with: "Good morning, and welcome to AI Dev Daily. I'm {host_name}, and today is {date}..."
"""

# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, dict] = {
    "claude": {
        "label": "Anthropic Claude",
        "default_model": "claude-sonnet-4-6",
        "max_tokens": 12000,
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o",
        "max_tokens": 12000,
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "label": "DeepSeek",
        "default_model": "deepseek-chat",
        "max_tokens": 8000,
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
    },
    "gemini": {
        "label": "Google Gemini",
        "default_model": "gemini-2.0-flash",
        "max_tokens": 12000,
        "env_key": "GEMINI_API_KEY",
    },
    "ollama": {
        "label": "Ollama (local)",
        "default_model": "llama3.1:8b",
        "max_tokens": 8000,
        "env_key": None,  # no key required
        "base_url": "http://localhost:11434/v1",
    },
}


# ---------------------------------------------------------------------------
# Per-provider call implementations
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, model: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_openai_compat(prompt: str, model: str, max_tokens: int, base_url: str, api_key: str) -> str:
    """Shared implementation for OpenAI, DeepSeek, Ollama (all OpenAI-compatible)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _call_gemini(prompt: str, model: str, max_tokens: int) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    client = genai.GenerativeModel(model)
    response = client.generate_content(
        prompt,
        generation_config={"max_output_tokens": max_tokens},
    )
    return response.text


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_script(
    articles: list[dict],
    date_str: Optional[str] = None,
    provider: str = "claude",
    model: Optional[str] = None,
) -> str:
    if date_str is None:
        date_str = datetime.now().strftime("%A, %B %d, %Y")

    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}")

    cfg = PROVIDERS[provider]
    chosen_model = model or os.environ.get("LLM_MODEL") or cfg["default_model"]
    max_tokens = cfg["max_tokens"]

    # Check required env var
    if cfg["env_key"] and not os.environ.get(cfg["env_key"]):
        raise EnvironmentError(
            f"Provider '{provider}' requires env var {cfg['env_key']} to be set."
        )

    trimmed = articles[:40]
    news_json = json.dumps(trimmed, indent=2, ensure_ascii=False)
    prompt = SCRIPT_PROMPT.format(
        podcast_name=PODCAST_NAME,
        date=date_str,
        news_json=news_json,
        host_name=HOST_NAME,
    )

    print(f"Generating podcast script with {cfg['label']} ({chosen_model})...")

    if provider == "claude":
        script = _call_claude(prompt, chosen_model, max_tokens)

    elif provider == "openai":
        script = _call_openai_compat(
            prompt, chosen_model, max_tokens,
            base_url="https://api.openai.com/v1",
            api_key=os.environ["OPENAI_API_KEY"],
        )

    elif provider == "deepseek":
        script = _call_openai_compat(
            prompt, chosen_model, max_tokens,
            base_url=cfg["base_url"],
            api_key=os.environ["DEEPSEEK_API_KEY"],
        )

    elif provider == "gemini":
        script = _call_gemini(prompt, chosen_model, max_tokens)

    elif provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", cfg["base_url"])
        script = _call_openai_compat(
            prompt, chosen_model, max_tokens,
            base_url=base_url,
            api_key="ollama",  # Ollama ignores the key but the SDK requires a non-empty value
        )

    word_count = len(script.split())
    print(f"Script generated: {word_count:,} words (~{word_count // 140} min at 140wpm)")
    return script


def list_providers() -> None:
    print("Available LLM providers:")
    for key, cfg in PROVIDERS.items():
        key_info = f"  (needs {cfg['env_key']})" if cfg["env_key"] else "  (no API key needed)"
        print(f"  {key:<10} {cfg['label']:<22} default model: {cfg['default_model']}{key_info}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate podcast script")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "claude"),
                        help="LLM provider (claude/openai/deepseek/gemini/ollama)")
    parser.add_argument("--model", help="Override the default model for the chosen provider")
    parser.add_argument("--list-providers", action="store_true", help="List available providers and exit")
    parser.add_argument("--news", default="news_cache.json", help="Path to news JSON cache")
    args = parser.parse_args()

    if args.list_providers:
        list_providers()
        raise SystemExit(0)

    with open(args.news, encoding="utf-8") as f:
        articles = json.load(f)

    script = generate_script(articles, provider=args.provider, model=args.model)
    date_tag = datetime.now().strftime("%Y-%m-%d")
    out_path = f"script_{date_tag}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Script saved to {out_path}")
