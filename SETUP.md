# AI Dev Daily — Setup Guide

## What this does

Every morning, this pipeline:
1. Collects AI news from ~14 RSS feeds + GitHub Trending
2. Uses an LLM (your choice of provider) to write a natural 60-min podcast script
3. Converts to MP3 via Azure TTS (neural voice)
4. Uploads MP3 to a GitHub Release
5. Updates an RSS feed on GitHub Pages
6. Your iPhone Apple Podcasts auto-downloads → syncs to Apple Watch

---

## One-time Setup (30-45 min)

### 1. Create the GitHub repo

```
gh repo create ai-dev-daily-podcast --public
cd ai-dev-daily-podcast
git checkout --orphan gh-pages
git rm -rf .
echo "<html><body>AI Dev Daily Podcast</body></html>" > index.html
git add index.html && git commit -m "init gh-pages"
git push origin gh-pages
git checkout -b main
```

Copy all files from this folder into the repo root, then push to main.

### 2. Enable GitHub Pages

In the repo → Settings → Pages → Source: **Deploy from a branch** → Branch: `gh-pages` → `/root`

Your feed will be at: `https://YOUR_USERNAME.github.io/ai-dev-daily-podcast/feed.xml`

### 3. Get API keys

You need one LLM key (pick any provider below) plus the Azure and GitHub keys.

---

#### Option A — DeepSeek (recommended: cheapest, great quality)

DeepSeek V3 is ~10× cheaper than Claude for this task (~$0.003/episode).

1. Go to [https://platform.deepseek.com](https://platform.deepseek.com) and click **Sign Up**
2. Register with your email address and verify it
3. After login, go to **API Keys** in the left sidebar (or visit `platform.deepseek.com/api_keys`)
4. Click **Create new API key**, give it a name (e.g. `ai-podcast`), copy the key — it starts with `sk-`
5. Add credit to your account: **Top Up** → minimum top-up is $2, which covers ~650 episodes
6. In your `.env` file set:
   ```
   LLM_PROVIDER=deepseek
   DEEPSEEK_API_KEY=sk-your-key-here
   ```
7. Test it:
   ```powershell
   python run_daily.py --provider deepseek --script-only
   ```

**DeepSeek models available:**
| Model | Best for | Context |
|-------|----------|---------|
| `deepseek-chat` | General use, fast (default) | 64K tokens |
| `deepseek-reasoner` | Complex analysis, slower | 64K tokens |

> **Note:** DeepSeek servers can be slow during peak hours (China business hours, ~01:00–10:00 UTC). The pipeline has no retries built in — if it fails, re-run manually or the GitHub Actions fallback will catch it.

---

#### Option B — Anthropic Claude

- Go to [https://console.anthropic.com](https://console.anthropic.com) → API Keys → Create key
- Cost: ~$0.03–0.05 per episode
- Set `LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY=sk-ant-...` in `.env`

---

#### Option C — OpenAI

- Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) → Create new secret key
- Cost: ~$0.05–0.10 per episode (GPT-4o)
- Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY=sk-...` in `.env`

---

#### Option D — Google Gemini

- Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → Create API key
- Free tier: 15 requests/minute, 1,500 requests/day — enough for daily use at no cost
- Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=...` in `.env`

---

#### Option E — Ollama (fully local, free)

Run a model on your own machine — no API key, no cost, no data leaves your PC.

1. Install Ollama: [https://ollama.com/download](https://ollama.com/download)
2. Pull a model (8B is fast; 70B is higher quality but needs a strong GPU):
   ```powershell
   ollama pull llama3.1:8b
   # or for better quality:
   ollama pull llama3.3:70b
   ```
3. Set in `.env`:
   ```
   LLM_PROVIDER=ollama
   LLM_MODEL=llama3.1:8b
   ```
4. Ollama must be running when the pipeline executes (`ollama serve` or the desktop app)

---

#### Switching providers later

Change `LLM_PROVIDER` in your `.env` at any time. You can also override per-run:
```powershell
python run_daily.py --provider deepseek
python run_daily.py --provider ollama --model llama3.3:70b
python run_daily.py --list-providers   # see all options
```

---

**Azure Speech** (for TTS audio):
- Go to https://portal.azure.com
- Create resource → "Speech" (Cognitive Services)
- Free tier (F0): 500K neural chars/month (~11 episodes free, then $16/1M chars)
- Copy your Key 1 and Region from the resource

**GitHub Token** (for uploading releases + updating feed):
- https://github.com/settings/tokens → Generate new token (classic)
- Scopes: `repo` (full), `workflow`
- Copy the token

### 4. Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env with your actual keys
notepad .env
```

### 5. Add GitHub Actions secrets

In your repo → Settings → Secrets and variables → Actions → New repository secret.

Required for everyone:
- `LLM_PROVIDER` — e.g. `deepseek`
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION` (e.g., `eastus`)
- `PODCAST_EMAIL`

Add only the key for your chosen provider:
- `DEEPSEEK_API_KEY` — if using DeepSeek
- `ANTHROPIC_API_KEY` — if using Claude
- `OPENAI_API_KEY` — if using OpenAI
- `GEMINI_API_KEY` — if using Gemini

(GITHUB_TOKEN is automatically provided by Actions)

### 6. Install Python dependencies + ffmpeg

```powershell
pip install -r requirements.txt
winget install ffmpeg   # or: choco install ffmpeg
```

### 7. Set up Windows Task Scheduler (local backup)

```powershell
# Run in elevated PowerShell
.\setup_windows_task.ps1
```

### 8. Test the pipeline

```powershell
# Load env vars first
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

# Test with script-only (no audio/upload, cheap)
python run_daily.py --script-only

# Full test without upload
python run_daily.py --skip-upload

# Full end-to-end
python run_daily.py
```

### 9. Subscribe on Apple Podcasts

1. Open Apple Podcasts on iPhone
2. Search tab → top-right `...` → Add a Podcast by URL
3. Enter: `https://YOUR_USERNAME.github.io/ai-dev-daily-podcast/feed.xml`
4. Tap Subscribe

**Enable auto-download to Watch:**
- iPhone Podcasts → Settings → AI Dev Daily → Auto-Download: ON
- Apple Watch Podcasts app → AI Dev Daily → Add to Library

---

## Daily flow (automatic)

- 5:00 AM UTC — GitHub Actions runs (always-on cloud backup)
- 6:30 AM local — Windows Task Scheduler runs (if PC is on)
- iPhone downloads episode overnight via WiFi
- Apple Watch syncs during phone charge
- Ready for your morning workout!

---

## Customizing content

Edit `collect_news.py` → `FEEDS` list to add/remove sources.

Edit `generate_script.py` → `HOST_NAME` and `SCRIPT_PROMPT` to adjust tone, topics, structure.

Edit `generate_audio.py` → `VOICE_NAME` for different voices:
- `en-US-GuyNeural` — male, clear (default)
- `en-US-JennyNeural` — female, warm
- `en-US-DavisNeural` — male, deeper
- `SPEECH_RATE = "+10%"` — faster for exercise

---

## Cost estimate (monthly, 30 episodes)

| Service | DeepSeek | Claude | OpenAI | Gemini | Ollama |
|---------|----------|--------|--------|--------|--------|
| LLM (script) | ~$0.09 | ~$1.20 | ~$2.00 | Free* | Free |
| Azure TTS | ~$0.13 | ~$0.13 | ~$0.13 | ~$0.13 | ~$0.13 |
| GitHub storage | Free | Free | Free | Free | Free |
| **Monthly total** | **~$0.22** | **~$1.33** | **~$2.13** | **~$0.13** | **~$0.13** |

\* Gemini free tier: 1,500 requests/day — more than sufficient for one episode/day.
