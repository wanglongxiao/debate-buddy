# Debate Buddy

**Live Demo:** [https://s7kuama4td669fv0835d5.apigateway-ap-southeast-1.apigw-byteplus.com/](https://s7kuama4td669fv0835d5.apigateway-ap-southeast-1.apigw-byteplus.com/)

Debate Buddy is an AI-powered debate research and practice assistant for
students and teams. It turns a motion, side, speaking time, and selected speaker
roles into a structured preparation pack with research, verified source links,
short arguments, rebuttals, and role-specific Word speeches.

## Core Features

- **AI-powered deep research** for both sides of a debate motion
- **Claim and evidence-chain verification** with source URLs, dates, source
  types, credibility labels, and explicit warnings when evidence is uncertain
- **Focused preparation** with a readable quick summary, three developed core
  arguments, four detailed responses and up to five cross-fire questions.
  Complete sentences are preserved; content is never cut off with ellipses.
- **Speaker drafts before evidence** in section 3, followed by the evidence bank
  in section 4: source excerpts, study context and method,
  dates, credibility, practical use and explicit limitations
- **Broader evidence**: aim for 5–8 distinct sourced findings across at least
  three dimensions, including limitations and opposing evidence. Research uses
  topic-specific English queries, public web pages and academic sources.
- **Case generation** with definitions, burdens, main arguments, clash
  analysis and attack-and-defense maps
- **Progressive speaker preparation** for every selected role, clearly labeled:
  first speakers define and build the case; second speakers rebut and add a
  distinct substantive; third speakers compare decisive clashes; reply/summary
  speakers develop both sides' strongest cases and weigh impact, likelihood,
  time frame and burdens. Role drafts update with the shared case and evidence.
- **Role-based Word export**: select pack sections and your role to generate
  a timed speech, outline and selected source material in a real `.docx` file
- **English, Chinese, and bilingual output**
- **Two-level left directory**: when multiple roles are selected, each role has
  a direct link under **Speaker Roles**. The current section and role follow
  scrolling. Role titles use a larger, bold font and distinct teal, blue,
  purple and amber colors for first, second, third and reply speakers.
  Single-role and historical packs remain supported.
- **Consistent section order** in the page, Markdown, refinement scope and Word
  material picker. English and Chinese interface labels include motion types,
  causal mechanisms, burdens, rebuttal targets and weighing.
- Visible copy buttons, Markdown and print-to-PDF export
- **Responsive Web UI** for desktop and mobile browsers
- **Guest and registered profiles** with isolated debate packs and secure
  password hashing
- **360-day persistent history** using SQLite locally or BytePlus TOS in the
  cloud, with search, update sorting, deletion, and automatic expiration
- **Fast, multi-round refinements** with automatic or explicit section scope;
  each request searches fresh evidence for the new topics, then returns changed
  sections and preserves untouched content. New/modified words are blue relative
  to the immediately preceding version; the next update resets the comparison.
- **Compact reading layout** with a fixed small header and a three-row update
  dock. Full update details, sources and conversation history open on demand.
- **Voice input** for motions, source notes and refinements: record up to
  25 seconds, stop to transcribe, edit appended text and submit; failed ASR can
  be retried without recording again
- **Saved versions** with three snapshots and one-click restore
- **Live generation progress** with current stage, source activity, elapsed
  time, input locking, and true request cancellation
- **Live debate coaching** at `/live`: prepared or new motions, required side
  and speaking round, speech summaries tagged by side/round, immediate rebuttal
  suggestions, questions, manual corrections, resume, and JSON summary export.
- **Shared WSD reasoning framework**: classify policy, actor-policy, value,
  comparison, regret and prediction motions; identify burdens, incentives and
  comparison worlds; link claims to causal warrants and impacts; distinguish
  direct rebuttal, mitigation, concession and weighing. Training examples are
  never factual evidence for a motion.

## 中文使用说明

准备包按以下顺序显示，也用于 Markdown 和 Word 资料选择：

1. 速读摘要
2. 辩题与定义
3. 各角色准备稿
4. 证据库
5. 核心论证
6. 攻防回应
7. 交叉质询

选择多个辩位后，左侧“各角色准备稿”下会出现一辩、二辩、三辩和总结辩的
二级菜单，仅显示实际选择的角色。点击即可定位到对应准备稿；角色标题用加大、
加粗字体和不同颜色区分。切换页面右上角的 English / 中文只改变界面文案，
生成内容的语言由“输出语言”单独决定。

底部更新框支持自动选择相关章节，也可以指定更新范围。Word 导出可选择资料章节
和目标辩位，多角色准备稿只加入目标角色的内容。实时分析入口位于顶部，
我方发言显示续讲建议，对方发言显示反驳切入点与争点权衡。

## Live Debate

Open **Live debate** in the header, or use the button on a preparation pack.
Choose the motion, your side and your speaking round. Choose the current
speaker's side and round before listening. **Pause and save** before changing
speakers, then resume. The microphone hears the room; this does not capture
system audio or automatically identify speakers. Both sides should speak in
turn. Overlapping speakers need manual correction.

The page has three areas: setup and listening controls at the top, current
speaker transcription on the left and response advice on the right, and questions/manual notes at the
bottom. During a match the page fits the viewport; records, advice and question
answers scroll inside their own panes. Records follow the newest turn
automatically. Scroll up to read history and use **Follow latest** to resume.
Advice and question answers use separate tabs so new automatic advice does not
replace a question answer. Narrow screens switch panes with tabs; language/ASR
settings, help and manual entry expand as overlays.
The left pane retains at most 1,200 characters of temporary transcription and
shows 24 saved summaries at a time; **Earlier** pages through older summaries,
and export includes every saved summary. Same-side speech produces continuation
priorities; opposing speech produces key claims, possible evidence/reasoning
gaps and a rebuttal. Advice replaces the previous suggestion and stays concise.
Summaries are saved before advice is generated. An interrupted turn can
be retried with the same event ID without creating duplicate records. Microphone
permission requires HTTPS or localhost.

There are three recognition modes:

- **Server ASR model**: set `ASR_PROVIDER=seed`, `SPEECH_API_KEY`,
  `SPEECH_ASR_URL=wss://voice.ap-southeast-1.bytepluses.com/api/v3/sauc/bigmodel_nostream`
  and `SPEECH_RESOURCE_ID=volc.seedasr.sauc.duration` for BytePlus Seed-Speech
  ASR 2.0. The adapter uses the independent speech service's `X-Api-Key`
  authentication and binary WebSocket protocol; `SPEECH_APPID` is retained for
  console reference and is not needed by this authentication mode. Account
  AK/SK and the text model API key are separate credentials.
  Alternatively set `ASR_PROVIDER=openai`, `ASR_URL` (full HTTPS
  `/audio/transcriptions` endpoint), `ASR_API_KEY` and `ASR_MODEL` for a compatible
  provider returning `{"text":"..."}`. `auto` prefers Seed when a speech key exists.
  The browser sends independent mono 16 kHz WAV chunks roughly every three
  seconds to `/api/live/sessions/{id}/transcribe/stream`. The Seed adapter uses
  the `/bigmodel` streaming WebSocket endpoint and returns partial and final
  transcription as HTTP NDJSON, without writing audio to disk. Pack dictation
  retains the configured `/bigmodel_nostream` endpoint. Seed streaming detects
  Chinese/English automatically. Allow the capture interval plus network/ASR
  time; this is short-chunk streaming, not a continuous browser WebSocket.
  The compatible OpenAI provider returns final results only.
  Recognition runs independently of summary/advice; confirmed speech is merged
  over about ten seconds for concise permanent summaries. Pausing sends the remaining partial
  chunk. Browser recognition flushes finalized text every ten seconds (or sooner
  for long text). The queue pauses capture when it falls behind.
- **Browser recognition**: available in supported browsers such as Chrome,
  independently of the configured text model. This uses the browser's speech
  service; it is not the site's configured ASR large model. Network access to
  that service may be required.
- **Manual input**: paste or type a speaker's turn when recognition is unavailable.

The current text ModelArk endpoint does not transcribe audio. Server ASR requires
separate provider credentials; no working ASR connection is assumed when they
are absent. Live summary/advice calls disable thinking, use at most 1,500 output
tokens, and have a per-call timeout set by `LIVE_LLM_TIMEOUT_SECONDS` (45 seconds
by default). Advice uses saved debate records and prepared material, without
live web verification. Spoken evidence is explicitly marked as unverified.
Summaries separate heard claims, reasons and impacts, and flag missing causal
links. Advice identifies the clash, response approach and weighing; an optional
focused check corrects overstated policy projections against evidence limitations.
POI hints are conditional on being after the first minute and before the last
minute of an opponent's substantive speech, and are omitted for reply speeches.

Only concise speaker-tagged summaries are permanently retained in SQLite
`live_sessions` / `live_records` or private TOS `<TOS_PREFIX>/live/`. They have
no application expiration and are separate from the preparation packs' 360-day
lifecycle. TOS live storage refuses to initialize if a bucket expiration rule
overlaps this prefix. Guest profiles owning live records are preserved during
cleanup, but a guest still needs the original session cookie to find them;
register the guest profile for future account access.

Raw audio and full transcripts are held only in current-page/request memory and
discarded after processing. Speech providers process the audio according to
their own policies. Unconfirmed browser interim words are placed in the manual
correction field when paused. Failed unsaved turns remain in page memory for
retry. Before leaving, pause and wait for the queue to finish; export saved
summaries for a local copy. Questions and generated advice are not retained.

## BytePlus Services

| Service | How Debate Buddy Uses It |
| --- | --- |
| **BytePlus ModelArk** | Generates compact evidence-based packs, section updates, role speeches and live coaching. |
| **BytePlus veFaaS** | Hosts the FastAPI application with elastic compute, request-level concurrency, and a minimum of one and maximum of two cloud instances. |
| **BytePlus API Gateway** | Provides the public HTTPS endpoint, forwards all Web UI and API routes to veFaaS, and supports long-running generation requests. |
| **BytePlus TOS** | Persists private user profiles, sessions, debate packs, messages, and versions across elastic instances, with 360-day lifecycle expiration for pack and session objects. |
| **BytePlus IAM / STS** | Authenticates deployment operations through a local BytePlus CLI profile. Account access keys are never included in the application package. |

## How It Works

1. Enter a debate motion.
2. Select Proposition or Opposition.
3. Choose the speech duration and one or more speaker roles.
4. Select Quick Prep, Standard Prep, or Deep Research.
5. Optionally provide notes, source excerpts, public URLs, or a mixture.
6. Debate Buddy researches the topic, writes the shared pack, then produces a
   focused set of drafts for every selected role. Progress, source activity and
   elapsed time stream throughout; short evidence banks may need a supplement.
7. Use the left directory and copy buttons. Choose **Word speech** to select
   source sections and your role. At the bottom, type or dictate a change and
   choose its section scope. Continue refining over multiple rounds.

The result includes:

- Quick summary
- Motion, definitions and both sides' burdens
- Progressive preparation drafts for every selected role
- Detailed evidence bank
- Three core arguments, causal mechanisms, impact comparison and the main risk
- Specific attack-and-defense responses and weighing
- Cross-fire questions and follow-ups

Team outline, role deep research, vocabulary and practice-plan modules are no
longer generated or displayed. Full timed speeches are generated only on Word
export. Generation and updates disable model thinking and enforce per-call
output limits. Refinements use the current pack and bounded recent requests.
Existing evidence facts are preserved unless new source text supports a correction.

Input dictation shares the configured Seed-Speech service with Live debate
through `/api/audio/transcribe`, without creating a live match. Audio remains
in memory. Transcribed text is appended to typed input and is never submitted
automatically. Choose Chinese or English beside the microphone button.

## Research and Evidence

Debate Buddy supports:

- Tavily
- Serper
- Brave Search
- Google Search through a local Chrome or Chromium browser
- OpenAlex academic research without an API key
- DuckDuckGo HTML fallback
- User-provided text and public source URLs

The automatic provider order is:

1. Tavily
2. Serper
3. Brave Search
4. Google Search with OpenAlex enrichment when a local browser is available
5. OpenAlex
6. DuckDuckGo

Low-quality social and document-sharing sources are filtered. Manual URLs are
validated to block private and local network addresses. Generated citations are
restricted to collected sources, and direct excerpts must match source text.
Missing details must be marked as unavailable.

## Technology

- Python 3.9+ locally and Python 3.12 on veFaaS
- FastAPI and Uvicorn
- Pydantic
- Jinja2
- SQLite for local history and BytePlus TOS for cloud persistence
- HTTPX and Beautiful Soup
- Playwright for optional local browser research
- Plain HTML, CSS, and JavaScript
- Locally bundled `docx-js` for Word downloads; no Node runtime needed in cloud

Rebuild the Word bundle after editing `web-tools/word-export.js`:

```bash
cd web-tools
npm ci
npm run build
```

## Local Setup

### Using `uv`

```bash
git clone https://github.com/wanglongxiao/debate-buddy.git
cd debate-buddy
uv venv --python 3.9
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env
```

Configure `.env`:

```dotenv
MODELARK_API_KEY=your_modelark_api_key
MODELARK_BASE_URL=https://ark.ap-southeast.bytepluses.com/api/v3
MAIN_AGENT_ENDPOINT=your_endpoint_id
```

Start the application:

```bash
./run_local.sh
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Using standard `pip`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `MODELARK_API_KEY` | Yes | BytePlus ModelArk API key |
| `MAIN_AGENT_ENDPOINT` | Yes | ModelArk endpoint ID |
| `MODELARK_BASE_URL` | No | ModelArk API base URL |
| `LLM_THINKING_MODE` | No | ModelArk thinking mode; defaults to `enabled` |
| `LLM_REASONING_EFFORT` | No | Reasoning effort; defaults to `low` |
| `LLM_MAX_TOKENS` | No | Combined reasoning and answer token limit; defaults to `120000` |
| `LLM_TIMEOUT_SECONDS` | No | Model request timeout; defaults to 900 seconds |
| `WEBPAGE_TIMEOUT_SECONDS` | No | Browser API request timeout; defaults to 900 seconds |
| `SEARCH_PROVIDER` | No | `auto`, `tavily`, `serper`, `brave`, `google`, `openalex`, or `duckduckgo` |
| `TAVILY_API_KEY` | No | Tavily search key |
| `SERPER_API_KEY` | No | Serper search key |
| `BRAVE_SEARCH_API_KEY` | No | Brave Search key |
| `GOOGLE_CHROME_PATH` | No | Custom Chrome or Chromium executable path |
| `STORAGE_BACKEND` | No | `sqlite`, `tos`, or `disabled`; defaults to `sqlite` |
| `ENABLE_LOCAL_HISTORY` | No | Legacy SQLite switch; defaults to `true` |
| `DATABASE_PATH` | No | SQLite database path |
| `BYTEPLUS_AK` | With TOS | BytePlus access key; set only as a secret |
| `BYTEPLUS_SK` | With TOS | BytePlus secret key; set only as a secret |
| `TOS_REGION` | With TOS | TOS region, such as `ap-southeast-1` |
| `TOS_BUCKET` | With TOS | Private TOS bucket name |
| `TOS_ENDPOINT` | With TOS | Native TOS endpoint; the app derives its S3-compatible endpoint |
| `TOS_PREFIX` | No | Object prefix; defaults to `debate-buddy/v1` |
| `DATA_RETENTION_DAYS` | No | Debate pack retention; defaults to 360 days |
| `RULES_CACHE_PATH` | No | Debate rules cache path |

Never commit real credentials. Use `.env` locally and veFaaS environment
variables in production.

## API

### Health

```bash
curl http://127.0.0.1:8000/api/health
```

The health response reports `storage_ready` and a sanitized `storage_error`.
If TOS is temporarily unavailable, the Web UI and health endpoint continue to
run in degraded mode while profile and history endpoints return HTTP 503.

### Generate a Debate Pack

```bash
curl -X POST http://127.0.0.1:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "motion": "This House would ban homework in middle schools.",
    "side": "Proposition",
    "speech_time_minutes": 4,
    "speaker_roles": ["1st Speaker", "2nd Speaker"],
    "language": "English",
    "research_depth": "Standard Prep",
    "source_material": "Notes, source excerpts, and https://example.org/report"
  }'
```

For live progress, use `POST /api/generate/stream` with the same JSON body.
The endpoint returns newline-delimited JSON events for research, evidence
evaluation, ModelArk reasoning, speech writing, source usage, and the final
result. Closing the stream, including by selecting **Stop generation** in the
Web UI, cancels the active server task and its in-flight model request.

### Profiles And History

```bash
curl 'http://127.0.0.1:8000/api/history?limit=20&offset=0&sort=desc&q=homework'
curl http://127.0.0.1:8000/api/history/GENERATION_ID
curl -N -X POST http://127.0.0.1:8000/api/history/GENERATION_ID/agent/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"Add this new viewpoint and strengthen the rebuttal."}'
curl -X POST http://127.0.0.1:8000/api/history/GENERATION_ID/versions
curl -X DELETE http://127.0.0.1:8000/api/history/GENERATION_ID
```

Local profiles, sessions, packs, messages, and versions are stored in SQLite.
The public veFaaS deployment stores them in a private BytePlus TOS bucket so
history remains available across elastic instances. Each browser starts as an
isolated Guest; registering preserves that Guest's packs. Packs not updated for
360 days are removed by both application cleanup and TOS lifecycle rules.

## Debate Rules

The application uses the shared coaching framework in
`app/services/debate_framework.py` across Pack, role drafts, Word speeches and
Live advice. Curated notes in `app/data/rules_notes.md` incorporate HMDC training
and WSDC speaker guidance. Conservative preparation choices for third/reply
speakers are distinguished from formal tournament rules.

The rules loader first reads `app/data/rules_notes.md`. When local notes are not
available, it downloads and caches public World Schools Debate reference
materials. If those sources cannot be reached, it falls back to built-in WSD
guidance.

Tournament-specific rules should always take priority.

## Security and Privacy

- The repository excludes `.env`, `uv.lock`, `.venv/`, `__pycache__/`,
  `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `.vefaas/`,
  `run_vefaas.sh`, `build/`, `dist/`, `docs/`, and `scripts/`. Diagnostic logs,
  PID files, screenshot captures and debug-output directories are also ignored.
  Most local helper tests are ignored; selected regression tests are tracked.
- BytePlus account AK/SK credentials are stored only in ignored local
  configuration or veFaaS environment variables. They are never included in
  Git commits or deployment archives.
- ModelArk credentials are injected through environment variables.
- The TOS bucket is private because it stores account data, session records,
  password hashes, and user-generated debate content.
- The application does not log full API keys.
- Debate prompts and selected source excerpts are sent to the configured
  ModelArk endpoint.
- AI output may contain mistakes. Open source links and verify important claims
  before using them in a tournament.
