"""
Collect AI news from RSS feeds, Hacker News, and GitHub trending.
Returns a list of article dicts with title, summary, url, source, date.
"""

import feedparser
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
import time

FEEDS = [
    # Official blogs
    ("Anthropic Blog", "https://www.anthropic.com/rss.xml"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("Meta AI", "https://ai.meta.com/blog/feed/"),
    # Newsletters / aggregators
    ("The Batch (DeepLearning.AI)", "https://www.deeplearning.ai/the-batch/feed/"),
    ("Import AI", "https://importai.substack.com/feed"),
    ("The Rundown AI", "https://www.therundown.ai/rss"),
    ("TLDR AI", "https://tldr.tech/ai/rss"),
    ("Ahead of AI", "https://magazine.sebastianraschka.com/feed"),
    # Dev-focused
    ("Simon Willison's Weblog", "https://simonwillison.net/atom/everything/"),
    ("Hacker News (AI/ML tagged)", "https://hnrss.org/newest?q=AI+LLM+claude+codex&points=20"),
    # Tools
    ("LangChain Blog", "https://blog.langchain.dev/rss/"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
]

CUTOFF_HOURS = 28  # articles newer than this


def fetch_feed(name: str, url: str, cutoff: datetime) -> list[dict]:
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:15]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

            if published and published < cutoff:
                continue

            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary[:800]
            elif hasattr(entry, "content"):
                summary = entry.content[0].value[:800]

            articles.append({
                "source": name,
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": summary,
                "published": published.isoformat() if published else "",
            })
        return articles
    except Exception as e:
        print(f"  [WARN] Failed to fetch {name}: {e}")
        return []


def fetch_github_trending() -> list[dict]:
    """Fetch trending AI/ML repos from GitHub."""
    try:
        url = "https://api.github.com/search/repositories"
        params = {
            "q": "topic:llm topic:ai created:>2026-05-01",
            "sort": "stars",
            "order": "desc",
            "per_page": 10,
        }
        resp = requests.get(url, params=params, timeout=10,
                            headers={"Accept": "application/vnd.github.v3+json"})
        if resp.status_code != 200:
            return []
        repos = resp.json().get("items", [])
        articles = []
        for r in repos[:8]:
            articles.append({
                "source": "GitHub Trending",
                "title": f"{r['full_name']} ⭐{r['stargazers_count']:,}",
                "url": r["html_url"],
                "summary": r.get("description", "") or "",
                "published": r.get("created_at", ""),
            })
        return articles
    except Exception as e:
        print(f"  [WARN] GitHub trending failed: {e}")
        return []


def collect_all() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CUTOFF_HOURS)
    all_articles: list[dict] = []

    print(f"Collecting news (cutoff: {CUTOFF_HOURS}h ago)...")
    for name, url in FEEDS:
        articles = fetch_feed(name, url, cutoff)
        print(f"  {name}: {len(articles)} articles")
        all_articles.extend(articles)
        time.sleep(0.3)

    trending = fetch_github_trending()
    print(f"  GitHub Trending: {len(trending)} repos")
    all_articles.extend(trending)

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in all_articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    print(f"Total unique items: {len(unique)}")
    return unique


if __name__ == "__main__":
    articles = collect_all()
    with open("news_cache.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(articles)} articles to news_cache.json")
