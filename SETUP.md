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
| `deepseek-v4-flash` | General use, fast (default) | 64K tokens |
| `deepseek-v4-pro` | Complex analysis, slower | 64K tokens |

> **Note:** `deepseek-chat` is deprecated as of 2026-07-24 — use `deepseek-v4-flash` instead (already the default in this pipeline).

> **Note:** DeepSeek servers can be slow during peak hours (China business hours, ~01:00–10:00 UTC). If script generation fails, re-run manually or the GitHub Actions fallback will catch it.

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

#### Option D — Groq (cheapest paid, ~$0.54/month, recommended)

Groq runs Llama models on custom silicon — very fast and the best quality-per-dollar option.
Cost: ~$0.018/episode ($0.59/M input + $0.79/M output tokens).

1. Go to [https://console.groq.com](https://console.groq.com) and sign up (Google/GitHub login available)
2. Go to **API Keys** → **Create API Key**, copy the key (starts with `gsk_`)
3. Add a payment method and top up (minimum varies — typically $5 covers months of use)
4. Set in `.env`:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_your-key-here
   ```
5. Test: `python run_daily.py --provider groq --script-only`

**Available models:**
| Model | Speed | Quality |
|-------|-------|---------|
| `llama-3.3-70b-versatile` | Fast | Best (default) |
| `llama-3.1-8b-instant` | Very fast | Good, lower quality |
| `gemma2-9b-it` | Fast | Good for structured text |

---

#### Option E — OpenRouter (free models, no credit card)

OpenRouter aggregates many providers, including some permanently free models.

1. Go to [https://openrouter.ai](https://openrouter.ai) → Sign up
2. Go to **Keys** → **Create Key**, copy it (starts with `sk-or-`)
3. No payment required for free-tier models
4. Set in `.env`:
   ```
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-your-key-here
   # Default model: meta-llama/llama-3.3-70b-instruct:free
   ```
5. To see all free models: [https://openrouter.ai/models?order=top&supported_parameters=free](https://openrouter.ai/models?order=top&supported_parameters=free)

> **Note:** Free models on OpenRouter can have rate limits and may be slower during peak hours.

---

#### Option F — Google Gemini

> **Warning:** Gemini requires billing to be enabled even for "free tier" usage. You will get a 429 quota error if your Google Cloud project has no payment method attached.

- Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → Create API key
- Enable billing in Google Cloud Console, then add credit
- Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=...` in `.env`

---

#### Option G — Ollama (fully local, free)

Run a model on your own machine — no API key, no cost, no data leaves your PC.

1. Install Ollama: [https://ollama.com/download](https://ollama.com/download)
2. Pull a model — pick based on your GPU VRAM:
   ```powershell
   # Gemma 4 (Google) — recommended for long-form writing
   ollama pull gemma4:2b     # ~2 GB  VRAM — fast, lower quality
   ollama pull gemma4:12b    # ~8 GB  VRAM — very good, best value (recommended)
   ollama pull gemma4:27b    # ~17 GB VRAM — excellent quality

   # Qwen 2.5 (Alibaba) — strong alternative
   ollama pull qwen2.5:7b    # ~5 GB  VRAM — good quality, fast
   ollama pull qwen2.5:14b   # ~10 GB VRAM — very good
   ollama pull qwen2.5:32b   # ~20 GB VRAM — excellent

   # Llama 3.3 (Meta)
   ollama pull llama3.3:70b  # ~40 GB VRAM — best open-source quality
   ```
   Both Gemma 4 and Qwen 2.5 outperform same-size Llama models for long-form writing.
3. Set in `.env`:
   ```
   LLM_PROVIDER=ollama
   LLM_MODEL=gemma4:12b
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
- Free tier (F0): 500K chars/month, but **per-request limit is ~3,500 chars** — the pipeline chunks automatically to work within this
- Paid tier (S0): $16/1M chars, no per-request limit — upgrade if you want fewer chunks / faster synthesis
- Copy your **Key 1** and **Region** from the resource (e.g. `australiaeast`)

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
- `AZURE_SPEECH_REGION` — your Azure region, e.g. `australiaeast`
- `PODCAST_EMAIL`

Add only the key for your chosen provider:
- `DEEPSEEK_API_KEY` — if using DeepSeek
- `ANTHROPIC_API_KEY` — if using Claude
- `OPENAI_API_KEY` — if using OpenAI
- `GEMINI_API_KEY` — if using Gemini
- `GROQ_API_KEY` — if using Groq
- `OPENROUTER_API_KEY` — if using OpenRouter

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

### 9. Subscribe and listen on Apple Watch

Do this once on your iPhone — after that everything is automatic.

**Step 1 — Subscribe on iPhone**

1. Open **Apple Podcasts** on iPhone
2. Open **Safari** on iPhone, navigate to:
   ```
   https://visualphyzx.github.io/ai-dev-daily-podcast/feed.xml
   ```
   iOS will offer to open it in Podcasts automatically — tap **Open**
   > Alternative: in Podcasts → **Library** → `+` → **Follow a Show by URL** → paste the URL above
3. Tap **Follow**

**Step 2 — Enable auto-download on iPhone**

1. In Podcasts → **Library** → **AI Dev Daily**
2. Tap `...` (top right) → **Settings**
3. Set **Download Episodes** → **New Episodes**

**Step 3 — Sync to Apple Watch**

1. On iPhone open the **Watch** app
2. Scroll down → **Podcasts**
3. Under **Add Episodes From** → select **AI Dev Daily**
4. Episodes sync to your Watch automatically overnight while both devices are charging

**Step 4 — Listen during your workout**

On your Apple Watch: **Podcasts app** → **Library** → **AI Dev Daily** → tap the episode → play.
Connects directly to AirPods or any Bluetooth headphones paired to the Watch — no iPhone needed outdoors.

---

## Daily flow (automatic)

```
6:30 AM local   Windows Task Scheduler generates new episode (PC must be on)
5:00 AM UTC     GitHub Actions generates episode (cloud backup, always runs)
      ↓
iPhone downloads episode automatically over WiFi
      ↓
Apple Watch syncs during overnight charge
      ↓
Morning workout → Watch Podcasts app → AI Dev Daily → Play
```

---

## Customizing content

Edit `collect_news.py` → `FEEDS` list to add/remove sources.

Edit `generate_script.py` → `HOST_NAME` and `SCRIPT_PROMPT` to adjust tone, topics, structure.

Edit `generate_audio.py` to change voice or speed:

**Current settings:**
- `VOICE_NAME = "en-GB-LibbyNeural"` — young female, England accent (default)
- `SPEECH_RATE = "-10%"` — slightly slower than normal for relaxed listening
- `SPEECH_PITCH = "+3%"` — slight lift to keep energy up

**Other voices to try:**
| Voice | Style |
|-------|-------|
| `en-GB-SoniaNeural` | Female, UK, professional |
| `en-GB-AbbiNeural` | Female, UK, softer |
| `en-US-JennyNeural` | Female, US, warm |
| `en-US-GuyNeural` | Male, US, clear |
| `en-AU-NatashaNeural` | Female, Australian |

> **Free tier note:** Azure F0 has a ~3,500 char per-request limit. `MAX_CHARS_PER_CHUNK = 3500` in `generate_audio.py` is set accordingly — don't increase it on the free tier.

---

## Cost estimate (monthly, 30 episodes)

| Service | Ollama | Groq | DeepSeek | Claude | OpenAI |
|---------|--------|------|----------|--------|--------|
| LLM (script) | **Free** | ~$0.54 | ~$0.09 | ~$1.20 | ~$2.00 |
| Azure TTS | ~$0.13 | ~$0.13 | ~$0.13 | ~$0.13 | ~$0.13 |
| GitHub storage | Free | Free | Free | Free | Free |
| **Monthly total** | **~$0.13** | **~$0.67** | **~$0.22** | **~$1.33** | **~$2.13** |

> Gemini requires billing enabled. OpenRouter has some permanently free models but with rate limits and variable availability.
