# Content Repurposing Pipeline

Turns one video transcript into everything needed to publish and promote the video:

- 5 YouTube titles to test
- A YouTube description with a search-friendly summary, chapters and key points
- 3 short-form scripts for YouTube Shorts or Reels
- A LinkedIn post
- An X (Twitter) thread

Everything can be copied piece by piece or downloaded as a single Markdown or text file.

## Who it is for

A YouTuber or content agency finishes a 30-minute video and then spends another hour or two writing
the title options, the description, clips and social posts. This app does that first draft from the
transcript in about a minute, using only what was said in the video, so the team edits instead of
starting from a blank page.

## Quick start (Windows)

Requires [Python 3.10 or newer](https://www.python.org/downloads/).

**Easiest:** double-click `run.bat`. The first run installs everything, then the app opens in your browser.

**Or run the commands yourself** from this folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

On macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

The app opens at http://localhost:8501. Press `Ctrl+C` in the terminal to stop it.

## Try it

1. Click **Load sample podcast transcript**. It loads a 27-minute interview from a fictional podcast.
2. Click **Generate Content Package**.
3. Go through the tabs: Titles, Description, Shorts scripts, LinkedIn post, X thread. Each block has a
   copy button in its top-right corner.
4. Click **Download all as Markdown** or **Download all as text**.

## Using your own transcripts

Add an API key first (next section). Then give the app a transcript in any of three ways:

- Paste a script or transcript into the text box.
- Upload a `.txt` file.
- Upload a `.srt` subtitle file. Subtitles are joined into paragraphs and keep a timestamp about
  every 30 seconds, so the description can list real chapter times.

Chapter timestamps are only written when the transcript contains them. With a plain script that has
no timings, the description lists chapters without times instead of guessing.

## Demo Mode and AI Mode

| | Demo Mode | AI Mode |
|---|---|---|
| Needs an API key | No | Yes |
| Sample transcript | Shows a saved example package | Generates a new package |
| Your own transcript | Not available | Generates a package |

Demo Mode is on when no key is configured. It exists so the app can be shown without an account;
the example package was written for the sample transcript and is not generated live.

To switch to AI Mode:

1. Copy `.env.example` to `.env`.
2. Paste **one** key:
   - Anthropic: `ANTHROPIC_API_KEY=...` (https://console.anthropic.com)
   - OpenAI: `OPENAI_API_KEY=...` (https://platform.openai.com)
   - Google Gemini: `GEMINI_API_KEY=...` (https://aistudio.google.com/apikey)
3. Restart the app. The sidebar shows the provider and model in use.

Never share your `.env` file or commit it to Git; `.gitignore` already excludes it.

| Setting | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | Which provider to use when more than one key is set: `anthropic`, `openai` or `gemini` |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | `claude-sonnet-5-5` and `claude-haiku-5-5` cost less |
| `OPENAI_MODEL` | `gpt-4o-mini` | Set to a chat model available on your account |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Any Gemini model your key can use |

Gemini offers a free tier. On it, Google may use the text you send to improve its products, so use the free tier for testing with sample data and a paid key for real client data.

## Project layout

| File | Role |
|---|---|
| `app.py` | The app screen: transcript input, tabs, downloads |
| `pipeline/models.py` | The `ContentPackage` schema: what gets generated and its limits |
| `pipeline/generator.py` | The editorial prompt and the Claude / OpenAI / Gemini calls |
| `pipeline/transcript.py` | Reads `.txt` and `.srt` uploads |
| `pipeline/export.py` | Builds the Markdown and text downloads |
| `pipeline/config.py` | Settings from `.env` |
| `sample_data/podcast_transcript.txt` | The sample transcript |
| `sample_data/demo_package.json` | The saved example package shown in Demo Mode |
| `tests/smoke_test.py` | End-to-end check, no API key needed |

Run the check with:

```powershell
.venv\Scripts\python.exe tests\smoke_test.py
```

## Notes for developers

- **Changing the house style.** The editorial brief is `SYSTEM_PROMPT` in `pipeline/generator.py`.
  Adjust it per client: tone, banned phrases, title conventions, whether to use hashtags.
- **Adding an output.** Add a field with a description to `ContentPackage`, then show it in `app.py`
  and include it in `pipeline/export.py`. The model reads the schema, so no other prompt change is needed.
- **Structured output.** With Claude the response is constrained to the schema, so the app always
  receives separate titles, scripts and posts rather than one block of text to parse.
- **Length limits.** X posts over 280 characters are flagged in the app rather than cut, so the editor
  decides what to trim.
- **Refusal fallback.** For current Claude models the request opts in to the server-side fallback
  (`fallbacks="default"`), so a transcript declined by a safety classifier is retried on another model
  instead of failing. Remove `betas` and `fallbacks` in `pipeline/generator.py` to turn it off.
- **Video and audio files.** The app starts from text. To accept a video file, add a transcription
  step (for example a speech-to-text API) that produces timestamped text and pass that in.
- **Privacy.** In AI Mode the transcript is sent to the chosen AI provider.
