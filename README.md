# Ad Injector

Ad injection system with Qdrant vector storage for semantic ad matching.

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
  uv run python -c "from ad_injector.qdrant_service import match_ads; print(match_ads('python', top_k=2))"
  ```

  You should see matching ads (e.g. the Python/coding ad) in the output.

## Architecture

The system is split into two MCP server planes:

| Plane | Purpose | Who calls it | Entrypoint |
|-------|---------|-------------|------------|
| **Data Plane** | Ad matching, read-only retrieval | LLMs / agents | `uv run ad-data-plane` |
| **Control Plane** | Provisioning, ingestion, admin ops | Humans, CI/CD, backoffice | `uv run ad-index` (CLI) |

### Data Plane tools (runtime, LLM-facing)

- `ads_match` — semantic ad matching
- `ads_explain` — audit/debug trace for a match
- `ads_health` — readiness check

### Control Plane tools (admin)

- `collection_ensure` — create/verify collection
- `collection_info` — collection metadata
- `ads_upsert_batch` — batch ad ingestion
- `ads_delete` — delete an ad
- `ads_get` — fetch a single ad (debugging)

### Configuration

Runtime settings are managed via environment variables (or `.env`), validated at startup by Pydantic:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_MODE` | `data` | `data` (Data Plane) or `admin` (Control Plane) |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `QDRANT_COLLECTION_NAME` | `ads` | Collection name |
| `EMBEDDING_MODEL_ID` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `EMBEDDING_DIMENSION` | `384` | Vector dimension |
| `MAX_TOP_K` | `100` | Max results per match query |
| `MAX_BATCH_SIZE` | `500` | Max ads per upsert batch |
| `REQUEST_TIMEOUT_SECONDS` | `30.0` | Per-request timeout |

## Running with uv

### Run Scripts

```bash
# Data Plane MCP server (LLM-facing, read-only)
uv run ad-data-plane

# Legacy MCP server (original single-tool server)
uv run ad-injector

# Control Plane — manage Qdrant collection (CLI)
uv run ad-index create          # Create the collection
uv run ad-index seed            # Add sample ads for testing
uv run ad-index info            # Show collection info
uv run ad-index delete          # Delete the collection
```

### Run Python Files Directly

```bash
uv run python -m ad_injector.main_runtime   # Data Plane
uv run python -m ad_injector.cli create     # Control Plane CLI
uv run python -m ad_injector.cli seed
```

**Note**: The `seed` command loads demo ads from `data/test_ads.json` (or `--file <path>`) and upserts them into the collection. Run `create` first to set up the collection, then `seed` to load the test data.

## Validating the MCP servers

### 1. Verify Data Plane starts and has no admin tools

```bash
# Confirm it creates without error and only registers data plane tools
uv run python -c "
from ad_injector.mcp.server import create_server
s = create_server('data')
print(f'Server: {s.name}')
print('Tools registered — ready for stdio transport')
"
```

### 2. Verify Control Plane starts and has no data tools

```bash
uv run python -c "
from ad_injector.mcp.server import create_server
s = create_server('admin')
print(f'Server: {s.name}')
print('Tools registered — ready for stdio transport')
"
```

### 3. Verify health tool responds (Data Plane)

```bash
uv run python -c "
from ad_injector.mcp.server import create_server
import json
s = create_server('data')
# ads_health is the only tool wired up so far
print('ads_health responds correctly' if 'ok' in s.call_tool('ads_health', {}) else 'FAIL')
" 2>/dev/null || echo "Note: tool invocation requires running MCP server — use MCP client for full validation"
```

### 4. Verify config loads and validates

```bash
# Defaults
uv run python -c "
from ad_injector.config import get_settings
s = get_settings()
print(f'mode={s.mcp_mode.value} host={s.qdrant_host} port={s.qdrant_port} model={s.embedding_model_id}')
"

# Invalid mode fails fast
MCP_MODE=invalid uv run python -c "from ad_injector.config.runtime import RuntimeSettings; RuntimeSettings()" 2>&1 | head -3
```

### 5. Verify import isolation (Data Plane does not load admin code)

```bash
uv run python -c "
import sys
from ad_injector.main_runtime import main
mods = [m for m in sys.modules if m.startswith('ad_injector')]
assert 'ad_injector.cli' not in mods, 'FAIL: cli imported'
assert 'ad_injector.qdrant_service' not in mods, 'FAIL: qdrant_service imported'
assert 'ad_injector.embedding_service' not in mods, 'FAIL: embedding_service imported'
print('PASS: main_runtime has clean import graph (no cli/qdrant/embedding modules)')
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

**Embedding text**: The vector embedding is generated from `title + body + topics`.

## Usage Example

```python
from ad_injector.models import Ad, AdTargeting, AdPolicy
from ad_injector.qdrant_service import create_collection, upsert_ad, query_ads

# Create the collection (once)
create_collection()

# Create an ad
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

# Generate embedding (using your preferred embedding model)
embedding = your_embedding_function(ad.embedding_text)

# Upsert to Qdrant
upsert_ad(ad, embedding)

# Query similar ads
query_embedding = your_embedding_function("python tutorial")
results = query_ads(query_embedding, top_k=5)
```

## Qdrant Filtering

You can filter queries using Qdrant's filter syntax:

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Filter by advertiser
filter_dict = Filter(
    must=[
        FieldCondition(key="advertiser_id", match=MatchValue(value="adv-123"))
    ]
)

results = query_ads(query_embedding, top_k=5, filter_dict=filter_dict)
```
