<div align="center">
  <img src="Adkit.png" alt="AdKit Logo">
  
  <p>
    <strong>A lightweight, semantic ad-engine for the LLMs, available through MCP</strong>
  </p>

  <p>
    <a href="https://python.org">
      <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
    </a>
    <a href="./LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
    </a>
    <img src="https://img.shields.io/badge/Architecture-Data%20%2F%20Control%20Plane-blueviolet" alt="Dual Plane Arch">
    <img src="https://img.shields.io/badge/MCP-Compatible-orange" alt="MCP Compatible">
  </p>

  <p align="center">
    🐦 <a href="https://twitter.com/charoori_ai">Follow Updates</a> •
    📧 <a href="mailto:chandrahas.aroori@gmail.com?subject=AdKit">Contact & Feedback</a>
  </p>

  <p>
    <a href="https://www.buymeacoffee.com/charoori_ai" target="_blank">
      <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="35">
    </a>
  </p>
</div>
<br/>

A simple MCP Server that serves advertisements to LLMs! Use this to Inject Advertisements from your sponsors in your LLM. 

## Introduction


**AdKit** is a lightweight semantic ad-matching engine built for **LLM applications**. It exposes a small, safe tool surface via **MCP** so agents can request relevant ads using natural-language context (chat turns, page content, search queries) — without brittle keyword rules.

Under the hood, AdKit embeds your context locally (FastEmbed) and retrieves candidates from **Qdrant** using vector similarity plus **typed constraints** (topics, locale, verticals, exclusions, policy flags). It’s designed with a hard security boundary: the **Data Plane** is read-only and allowlisted, while the **Control Plane** handles ingestion and admin operations separately.

Use it when you want “native” sponsor inserts or product recommendations that match meaning, not strings — and you want the architecture to stay sane when you ship to production.


## Where can you use this?
- AI Agents & Assistants: Seamlessly inject relevant product recommendations or sponsored messages into chat interfaces (e.g., customer support bots, shopping assistants).

- RAG (Retrieval-Augmented Generation) Pipelines: Serve "sponsored context" alongside organic retrieval results, allowing for high-relevance native advertising in search or Q&A tools.

- Content Discovery Platforms: Power "You might also like" features or affiliate link insertion based on the semantic meaning of the content being consumed, rather than fragile keyword matching.

OR [**take inspiration from the architecture**](#architecture)

## Prerequisites

- Python 3.10
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- [Qdrant](https://qdrant.tech/) - Running locally

## Setup

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Start Qdrant Locally

```bash
# Using Docker
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Or download binary from https://github.com/qdrant/qdrant/releases
```

### Install Dependencies

```bash
# Install all dependencies and create virtual environment
uv sync
```

### Configure Environment (Optional)

```bash
# Copy example env file (defaults work for local Qdrant)
cp .env.example .env
```

## Demo ads setup (step-by-step)

Follow these steps in order to load demo ads and confirm everything works. Demo ads are defined in `data/test_ads.json`; re-running `seed` upserts them so the store matches the file.

**Step 1.** Start Qdrant (in a terminal):

```bash
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  qdrant/qdrant

docker ps --filter name=qdrant
```

**Step 2.** In the project directory, install dependencies:

```bash
uv sync
```

**Step 3.** (Optional) Copy env:

```bash
cp .env.example .env
```

**Step 4.** Create the collection:

```bash
uv run ad-index create 
```

If it exists (uv run ad-index delete)

**Step 5.** Load demo ads from the file:

```bash
uv run ad-index seed
```

To use a different file: `uv run ad-index seed --file path/to/ads.json`

**Step 6.** Verify it worked:

- Run:

  ```bash
  uv run ad-index info
  ```

  Confirm **Points count** is 5 (or the number of ads in your JSON file).

- Optionally, query ads from Python to confirm they are being served:

  ```bash
  uv run python -c "
  from ad_injector.wiring import build_match_service
  from ad_injector.models.mcp_requests import MatchRequest
  r, _ = build_match_service().match(MatchRequest(context_text='python', top_k=2))
  print(r.model_dump_json(indent=2))
  "
  ```

  You should see matching ads (e.g. the Python/coding ad) in the output.

## Architecture

The system is split into two MCP server planes:

| Plane | Purpose | Who calls it | Entrypoint |
|-------|---------|-------------|------------|
| **Data Plane** | Ad matching, read-only retrieval | LLMs / agents | `uv run ad-mcp-data` or `uv run ad-data-plane` |
| **Control Plane** | Provisioning, ingestion, admin ops | Humans, CI/CD, backoffice | `uv run ad-mcp-control` or `uv run ad-index` (CLI) |

Run two separate processes for production: one Control Plane (admin) and one Data Plane (runtime). Each has its own auth scope (optional `MCP_ADMIN_KEY` / `MCP_DATA_KEY`).

### Data Plane tools (runtime, LLM-facing)

- `ads_match` — semantic ad matching (context_text, placement, constraints, top_k); returns candidates and match_id for explain
- `ads_explain` — audit trace for a prior match (match_id)
- `ads_health` — liveness/readiness (Qdrant + embedding)
- `ads_capabilities` — supported placements, constraint keys, embedding model, schema version

The Data Plane uses an explicit allowlist (`DATA_PLANE_ALLOWED_TOOLS`). No destructive or admin tools can be registered.

### Control Plane tools (admin)

- `collection_ensure` — create/align collection (dimension, embedding_model_id, schema_version)
- `collection_info` — collection metadata (points_count, dimension, embedding_model_id, schema_version)
- `collection_migrate` — optional schema migrations (from_version, to_version)
- `ads_upsert_batch` — batch ad ingestion (JSON array)
- `ads_delete` — delete an ad by id
- `ads_bulk_disable` — set enabled=false for ads matching a filter (JSON filter)
- `ads_get` — fetch a single ad (debugging)

### Repo structure

```
src/ad_injector/
  models/           # Ad, Targeting, Policy; MCP request/response DTOs
  services/         # MatchService, PolicyEngine, TargetingEngine, IndexService
  adapters/         # QdrantVectorStore, FastEmbedProvider
  mcp/              # server, tools, auth, observability
  config/           # RuntimeSettings, env vars
  ops/              # smoke_check, migrations
```

### Configuration

Runtime settings are managed via environment variables (or `.env`), validated at startup by Pydantic:

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `QDRANT_COLLECTION_NAME` | `ads` | Collection name |
| `EMBEDDING_MODEL_ID` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `EMBEDDING_DIMENSION` | `384` | Vector dimension |
| `MAX_TOP_K` | `100` | Max results per match query |
| `MAX_BATCH_SIZE` | `500` | Max ads per upsert batch |
| `REQUEST_TIMEOUT_SECONDS` | `30.0` | Per-request timeout |
| `REQUIRE_ADMIN_KEY` | `false` | If true, Control Plane requires `MCP_ADMIN_KEY` env |
| `REQUIRE_DATA_KEY` | `false` | If true, Data Plane requires `MCP_DATA_KEY` env |

## Running with uv

### Run Scripts

```bash
# Data Plane MCP server (LLM-facing, read-only): ads_match, ads_explain, ads_health, ads_capabilities
uv run ad-mcp-data
# or: uv run ad-data-plane

# Control Plane MCP server (admin): collection.*, ads.upsert_batch, ads.delete, ads.bulk_disable, ads.get
uv run ad-mcp-control

# CLI (Control Plane): create collection, seed ads, info, delete
uv run ad-index create          # Create the collection
uv run ad-index seed            # Add sample ads for testing
uv run ad-index info            # Show collection info
uv run ad-index delete          # Delete the collection
```

### Run Python Files Directly

```bash
uv run python -m ad_injector.main_runtime   # Data Plane MCP
uv run python -m ad_injector.main_control   # Control Plane MCP
uv run python -m ad_injector.cli create     # Control Plane CLI
uv run python -m ad_injector.cli seed
```

**Note**: The `seed` command loads demo ads from `data/test_ads.json` (or `--file <path>`) and upserts them into the collection. Run `create` first to set up the collection, then `seed` to load the test data.

## Validating the MCP servers

### 1. Run the test suite

```bash
uv run pytest tests/ -v
```

This runs the Data Plane guardrail tests which assert:
- Data Plane exposes only the allowlisted tools (`ads_match`, `ads_explain`, `ads_health`, `ads_capabilities`)
- No forbidden/destructive tools on the Data Plane
- Control Plane has admin tools and does **not** expose Data Plane–only tools

### 2. Verify Data Plane exposes the allowlisted tools

```bash
uv run python -c "
from ad_injector.mcp.server import create_server
from ad_injector.mcp.tools import DATA_PLANE_ALLOWED_TOOLS
s = create_server('data')
tools = set(s._tool_manager._tools.keys())
print(f'Server: {s.name}')
print(f'Tools:  {tools}')
assert tools == DATA_PLANE_ALLOWED_TOOLS, f'FAIL: expected {DATA_PLANE_ALLOWED_TOOLS}'
print('PASS: Data Plane allowlist registered')
"
```

### 3. Verify Control Plane starts with admin tools

```bash
uv run python -c "
from ad_injector.mcp.server import create_server
s = create_server('admin')
tools = set(s._tool_manager._tools.keys())
print(f'Server: {s.name}')
print(f'Tools:  {tools}')
assert 'ads_match' not in tools, 'FAIL: ads_match on admin plane'
assert 'collection_ensure' in tools
print('PASS: admin tools registered, no ads_match')
"
```

### 4. Verify ads_match DTO validation

```bash
uv run python -c "
from ad_injector.models import MatchRequest, MatchConstraints, PlacementContext, MatchResponse, AdCandidate

# Valid request
req = MatchRequest(
    context_text='I want to learn Python',
    top_k=5,
    placement=PlacementContext(placement='sidebar', surface='chat'),
    constraints=MatchConstraints(topics=['python'], locale='en-US', sensitive_ok=False),
)
print(f'MatchRequest OK: context_text={req.context_text!r}, top_k={req.top_k}')
print(f'  constraints.topics={req.constraints.topics}, locale={req.constraints.locale}')

# Valid response
resp = MatchResponse(
    candidates=[AdCandidate(ad_id='ad-001', advertiser_id='adv-1', title='Learn Python',
        body='Courses', cta_text='Go', landing_url='https://example.com', score=0.95, match_id='m-1')],
    request_id='req-xyz', placement='sidebar',
)
print(f'MatchResponse OK: {len(resp.candidates)} candidate(s)')

# Invalid request (empty context) fails
try:
    MatchRequest(context_text='', top_k=5)
    print('FAIL: empty context_text should be rejected')
except Exception:
    print('PASS: empty context_text rejected')
"
```

### 5. Verify config loads and validates

```bash
# Defaults
uv run python -c "
from ad_injector.config import get_settings
s = get_settings()
print(f'host={s.qdrant_host} port={s.qdrant_port} model={s.embedding_model_id}')
"

# Invalid port fails fast
QDRANT_PORT=99999 uv run python -c "from ad_injector.config.runtime import RuntimeSettings; RuntimeSettings()" 2>&1 | head -3
```

### 6. Verify import isolation (Data Plane does not load admin code)

```bash
uv run python -c "
import sys
from ad_injector.main_runtime import main
mods = [m for m in sys.modules if m.startswith('ad_injector')]
assert 'ad_injector.cli' not in mods, 'FAIL: cli imported'
print('PASS: main_runtime has clean import graph (no admin modules)')
"
```

### Add Dependencies

```bash
uv add <package-name>           # Add a dependency
uv add --dev <package-name>     # Add a dev dependency
```

## Ad Schema

Each ad stored in Qdrant contains:

| Field | Type | Description |
|-------|------|-------------|
| `ad_id` | string | Unique identifier for the ad |
| `advertiser_id` | string | Identifier for the advertiser |
| `title` | string | Ad headline |
| `body` | string | Ad body text |
| `cta_text` | string | Call-to-action text |
| `landing_url` | string | Redirect URL |
| `targeting.topics` | string[] | Topics to target |
| `targeting.locale` | string[] | Locale codes (e.g., "en-US") |
| `targeting.verticals` | string[] | Industry verticals |
| `targeting.blocked_keywords` | string[] | Keywords to exclude |
| `policy.sensitive` | boolean | Sensitive content flag |
| `policy.age_restricted` | boolean | Age restriction flag |
| `enabled` | boolean | Whether the ad is eligible for matching (default `true`; `ads_bulk_disable` sets `false`) |

**Embedding text**: The vector embedding is generated from `title + body + topics`.

## Usage Example

```python
from ad_injector.models import Ad, AdTargeting, AdPolicy
from ad_injector.wiring import build_index_service, build_match_service
from ad_injector.models.mcp_requests import MatchRequest

# Create the collection (once) and seed ads via IndexService
index_svc = build_index_service()
index_svc.ensure_collection()
ad = Ad(
    ad_id="ad-001",
    advertiser_id="adv-123",
    title="Learn Python Today",
    body="Master Python programming with our interactive courses.",
    cta_text="Start Learning",
    landing_url="https://example.com/python",
    targeting=AdTargeting(
        topics=["programming", "python", "education"],
        locale=["en-US"],
        verticals=["education", "technology"],
    ),
    policy=AdPolicy(sensitive=False, age_restricted=False),
)
index_svc.upsert_ads([ad])

# Match ads via MatchService (Data Plane logic)
match_svc = build_match_service()
response, audit_trace = match_svc.match(
    MatchRequest(context_text="python tutorial", top_k=5)
)
for c in response.candidates:
    print(f"{c.ad_id}: {c.title} (score={c.score}, match_id={c.match_id})")
```

## `ads_match` request / response schemas

The Data Plane `ads_match` tool uses typed DTOs — no raw dict filters are accepted.

### Request parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `context_text` | string (1-10000 chars) | *required* | Conversational / page context to match against |
| `top_k` | int (1-100) | `5` | Number of candidates to return |
| `placement` | string | `"inline"` | Placement slot (e.g. `inline`, `sidebar`, `banner`) |
| `surface` | string | `"chat"` | Surface type (e.g. `chat`, `search`, `feed`) |
| `topics` | string[] \| null | `null` | Restrict to these topics |
| `locale` | string \| null | `null` | Required locale (e.g. `en-US`) |
| `verticals` | string[] \| null | `null` | Restrict to these verticals |
| `exclude_advertiser_ids` | string[] \| null | `null` | Advertiser IDs to exclude |
| `exclude_ad_ids` | string[] \| null | `null` | Ad IDs to exclude |
| `age_restricted_ok` | bool | `false` | Allow age-restricted ads |
| `sensitive_ok` | bool | `false` | Allow sensitive-content ads |

### Response shape

```json
{
  "candidates": [
    {
      "ad_id": "ad-001",
      "advertiser_id": "adv-123",
      "title": "Learn Python Today",
      "body": "Master Python programming...",
      "cta_text": "Start Learning",
      "landing_url": "https://example.com/python",
      "score": 0.95,
      "match_id": "m-abc123"
    }
  ],
  "request_id": "req-xyz-456",
  "placement": "sidebar"
}
```

- `match_id` can be passed to `ads_explain` for audit traces (why eligible/ineligible, filters, scores)
- `score` is cosine similarity (0-1)


## Talk to me

I’m always up for nerding out about MCP tooling, retrieval systems, and practical LLM monetization.  
If you’re building something similar—or want to pressure-test your architecture—reach out:

- 🐦 Twitter: https://twitter.com/charoori_ai  
- 📧 Email: mailto:chandrahas.aroori@gmail.com?subject=AdKit
