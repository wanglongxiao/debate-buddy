# Debate Buddy

**Live Demo:** [https://s6f6mbgn5klufecacfd5j.apigateway-ap-southeast-1.apigw-byteplus.com/](https://s6f6mbgn5klufecacfd5j.apigateway-ap-southeast-1.apigw-byteplus.com/)

Debate Buddy is an AI-powered debate research and practice assistant for
students and teams. It turns a motion, side, speaking time, and selected speaker
roles into a structured preparation pack with research, verified source links,
argument chains, rebuttals, speeches, and practical exercises.

## Core Features

- **AI-powered deep research** for both sides of a debate motion
- **Claim and evidence-chain verification** with source URLs, dates, source
  types, credibility labels, and explicit warnings when evidence is uncertain
- **Human-friendly debate practice** with simple explanations, speaking lines,
  cross-fire questions, vocabulary, and a step-by-step practice plan
- **Team case generation** with definitions, burdens, main arguments, clash
  analysis, attack-and-defense maps, and a complete team split
- **Individual speaker preparation** for first, second, third, and
  reply/summary speakers
- **Debate speech generation**, including a complete first-speaker speech and
  role-specific outlines and scripts
- **English, Chinese, and bilingual output**
- **Markdown export, section copying, and print-to-PDF support**
- **Responsive Web UI** for desktop and mobile browsers
- **Guest and registered profiles** with isolated debate packs and secure
  password hashing
- **Local 360-day history** using SQLite, with search, update sorting, deletion,
  automatic expiration, and cleanup
- **Living debate packs** with an AI update prompt, three saved versions, and
  one-click version restore
- **Live generation progress** with current stage, source activity, elapsed
  time, input locking, and true request cancellation

## BytePlus Services

| Service | How Debate Buddy Uses It |
| --- | --- |
| **BytePlus ModelArk** | Runs the language model workflow for motion analysis, evidence evaluation, argument construction, rebuttal planning, speech writing, and vocabulary generation. |
| **BytePlus veFaaS** | Hosts the stateless FastAPI application with elastic compute, request-level concurrency, and a minimum of one and maximum of two cloud instances. |
| **BytePlus API Gateway** | Provides the public HTTPS endpoint, forwards all Web UI and API routes to veFaaS, and supports long-running generation requests. |
| **BytePlus IAM / STS** | Authenticates deployment operations through a local BytePlus CLI profile. Account access keys are never included in the application package. |

## How It Works

1. Enter a debate motion.
2. Select Proposition or Opposition.
3. Choose the speech duration and one or more speaker roles.
4. Select Quick Prep, Standard Prep, or Deep Research.
5. Optionally provide notes, source excerpts, public URLs, or a mixture.
6. Debate Buddy researches the topic, evaluates evidence, builds the case, and
   generates team and individual preparation materials while streaming the
   current stage, source activity, and elapsed time to the browser.

The result includes:

- Motion understanding and key definitions
- Proposition and opposition burdens
- Main arguments and strategic priorities
- Attack-and-defense map
- Cross-fire questions and follow-ups
- Team speaker outline
- First-speaker speech
- Role-specific research and speech text
- Evidence bank
- Vocabulary builder
- Practice plan

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
validated to block private and local network addresses. The application keeps
real source information when AI evaluation fails and never invents replacement
citations.

## Technology

- Python 3.9+ locally and Python 3.12 on veFaaS
- FastAPI and Uvicorn
- Pydantic
- Jinja2
- SQLite for optional local history
- HTTPX and Beautiful Soup
- Playwright for optional local browser research
- Plain HTML, CSS, and JavaScript

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
| `LLM_TIMEOUT_SECONDS` | No | Model request timeout; defaults to 1800 seconds |
| `WEBPAGE_TIMEOUT_SECONDS` | No | Browser API request timeout; defaults to 1800 seconds |
| `SEARCH_PROVIDER` | No | `auto`, `tavily`, `serper`, `brave`, `google`, `openalex`, or `duckduckgo` |
| `TAVILY_API_KEY` | No | Tavily search key |
| `SERPER_API_KEY` | No | Serper search key |
| `BRAVE_SEARCH_API_KEY` | No | Brave Search key |
| `GOOGLE_CHROME_PATH` | No | Custom Chrome or Chromium executable path |
| `ENABLE_LOCAL_HISTORY` | No | Enables SQLite history; defaults to `true` locally |
| `DATABASE_PATH` | No | SQLite database path |
| `DATA_RETENTION_DAYS` | No | Local history retention; defaults to 360 days |
| `RULES_CACHE_PATH` | No | Debate rules cache path |

Never commit real credentials. Use `.env` locally and veFaaS environment
variables in production.

## API

### Health

```bash
curl http://127.0.0.1:8000/api/health
```

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

### Local History

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
Each browser starts as an isolated Guest; registering preserves that Guest's
packs. Packs not updated for 360 days are removed automatically. The public
veFaaS deployment disables profiles and local history so requests remain
stateless across elastic instances.

## Debate Rules

The application first reads `app/data/rules_notes.md`. When local notes are not
available, it downloads and caches public World Schools Debate reference
materials. If those sources cannot be reached, it falls back to built-in WSD
guidance.

Tournament-specific rules should always take priority.

## Security and Privacy

- `.env`, credentials, caches, databases, test files, and local environments
  are excluded from Git and cloud deployment packages.
- BytePlus account AK/SK credentials are used only by the local CLI profile.
- ModelArk credentials are injected through environment variables.
- The application does not log full API keys.
- Debate prompts and selected source excerpts are sent to the configured
  ModelArk endpoint.
- AI output may contain mistakes. Open source links and verify important claims
  before using them in a tournament.
