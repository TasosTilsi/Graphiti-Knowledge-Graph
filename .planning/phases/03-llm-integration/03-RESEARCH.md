# Phase 3: LLM Integration - Research

**Researched:** 2026-02-04
**Domain:** Hybrid cloud/local Ollama integration with failover and quota management
**Confidence:** HIGH

## Summary

This phase implements hybrid cloud/local Ollama integration with graceful degradation. Research focused on the Ollama Python client (v0.6.1), official Ollama cloud service, retry/failover patterns, and request queueing for failed LLM calls.

The standard approach uses the official `ollama` Python library for both cloud and local connections, with cloud as primary (requires `OLLAMA_API_KEY` and account) and local as fallback (no auth). Error handling follows a retry-then-failover pattern: on any cloud error, retry with fixed delay, then fall back to local. Rate-limit errors (429) trigger a 10-minute cooldown before retrying cloud.

Ollama's cloud service launched in 2026 with three tiers (Free/Pro/Max) offering usage-based quotas for cloud models. The API uses standard HTTP status codes (200/400/404/429/500/502) with JSON error responses. The Python client raises `ResponseError` with `status_code` and `error` attributes for all failures.

**Primary recommendation:** Use `ollama` library with `tenacity` for retry logic, `persist-queue` for failed request queueing, and structured logging to track failover events.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ollama | 0.6.1 | Ollama Python client | Official library, supports both sync/async, cloud and local endpoints |
| tenacity | 9.1.2 | Retry logic with decorators | Apache 2.0, mature library for retry patterns with fixed/exponential backoff |
| httpx | latest | HTTP client (used by ollama) | Modern async-capable HTTP client with granular timeout control |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| persist-queue | 1.1.0 | Persistent disk-based queues | Queue failed LLM requests for background retry (SQLiteAckQueue) |
| structlog | latest | Structured logging | Track failover events, quota warnings, errors in machine-readable format |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tenacity | Custom retry loop | Tenacity provides tested edge cases, async support, composable conditions |
| persist-queue | Redis Queue (RQ) | RQ requires Redis server, persist-queue is file/SQLite (zero deps) |
| structlog | Standard logging | structlog adds structured context, better for observability tools |

**Installation:**
```bash
pip install ollama==0.6.1 tenacity==9.1.2 persist-queue==1.1.0 structlog
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── llm/
│   ├── client.py           # OllamaClient with failover logic
│   ├── quota.py            # Quota tracking and warnings
│   ├── queue.py            # Failed request queue management
│   └── config.py           # Configuration (endpoints, models, timeouts)
├── config/
│   └── llm.toml            # LLM configuration file
└── utils/
    └── logging.py          # Structured logging setup
```

### Pattern 1: Primary/Fallback with Retry
**What:** Cloud-first with automatic local fallback on errors
**When to use:** Any LLM operation (chat, generate, embed)
**Example:**
```python
# Simplified pattern - actual implementation uses tenacity decorators
from ollama import Client, ResponseError
import time

class OllamaClient:
    def __init__(self, cloud_host, local_host, api_key):
        self.cloud = Client(host=cloud_host,
                           headers={'Authorization': f'Bearer {api_key}'},
                           timeout=90.0)
        self.local = Client(host=local_host, timeout=90.0)
        self.cloud_cooldown_until = 0  # Unix timestamp

    def chat(self, model, messages, **kwargs):
        # Try cloud if not in cooldown
        if time.time() >= self.cloud_cooldown_until:
            try:
                return self._retry_cloud(model, messages, **kwargs)
            except ResponseError as e:
                if e.status_code == 429:
                    # Rate limit: 10-min cooldown
                    self.cloud_cooldown_until = time.time() + 600
                    logger.warning("Rate limited, cooldown 10min")
                else:
                    # Other error: retry cloud on next request
                    logger.warning(f"Cloud error {e.status_code}: {e.error}")
                # Fall through to local

        # Fallback to local
        return self._try_local(model, messages, **kwargs)

    def _retry_cloud(self, model, messages, **kwargs):
        # Use tenacity decorator for actual retry logic
        # 3 attempts (1 initial + 2 retries), 10s fixed delay
        pass

    def _try_local(self, model, messages, **kwargs):
        # Try local, or queue and raise if fails
        pass
```

### Pattern 2: Quota Tracking via Headers
**What:** Parse response headers to track cloud usage
**When to use:** After every successful cloud request
**Example:**
```python
# Ollama cloud may include quota headers (verify in production)
# If not available, use local counting as fallback

class QuotaTracker:
    def __init__(self, warning_threshold=0.8):
        self.warning_threshold = warning_threshold
        self.requests_made = 0  # Fallback: local counting

    def update(self, response_headers):
        # Attempt to parse quota headers (if available)
        # X-RateLimit-Remaining, X-RateLimit-Limit, etc.
        remaining = response_headers.get('x-ratelimit-remaining')
        limit = response_headers.get('x-ratelimit-limit')

        if remaining and limit:
            usage = 1 - (int(remaining) / int(limit))
            if usage >= self.warning_threshold:
                logger.warning(f"Quota at {usage*100:.1f}%")
        else:
            # Fallback: increment local counter
            self.requests_made += 1
```

### Pattern 3: Persistent Queue for Failed Requests
**What:** SQLite-backed queue stores failed requests for later retry
**When to use:** When both cloud and local fail
**Example:**
```python
from persist_queue import SQLiteAckQueue
import uuid

class LLMRequestQueue:
    def __init__(self, path='~/.graphiti/llm_queue'):
        self.queue = SQLiteAckQueue(path, auto_commit=True)

    def enqueue(self, operation, params):
        request_id = str(uuid.uuid4())
        self.queue.put({
            'id': request_id,
            'operation': operation,
            'params': params,
            'timestamp': time.time()
        })
        return request_id

    def process_pending(self, client):
        # Background retry logic
        item = self.queue.get(block=False)
        if item:
            try:
                # Retry request
                result = client.call(item['operation'], **item['params'])
                self.queue.ack(item)  # Success
                return result
            except Exception as e:
                self.queue.nack(item)  # Return to queue
                raise
```

### Pattern 4: Configuration Management
**What:** TOML-based configuration with environment variable overrides
**When to use:** Application startup
**Example:**
```python
# llm.toml
[cloud]
provider = "ollama"  # Official Ollama cloud
endpoint = "https://ollama.com"
default_model = "gpt-oss:120b-cloud"

[local]
endpoint = "http://localhost:11434"
auto_start = false  # Don't auto-start Ollama service
models = ["gemma2:9b", "llama3.2:3b"]  # Fallback chain

[embeddings]
model = "nomic-embed-text"

[retry]
max_attempts = 3  # 1 initial + 2 retries
delay_seconds = 10  # Fixed delay
timeout_seconds = 90

[quota]
warning_threshold = 0.8  # Warn at 80%

[logging]
failover_events = true  # Log every failover
```

```python
# config.py
import tomllib
import os

def load_config():
    config_path = os.getenv('GRAPHITI_LLM_CONFIG', '~/.graphiti/llm.toml')
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)

    # Environment overrides
    if api_key := os.getenv('OLLAMA_API_KEY'):
        config['cloud']['api_key'] = api_key
    if endpoint := os.getenv('OLLAMA_CLOUD_ENDPOINT'):
        config['cloud']['endpoint'] = endpoint

    return config
```

### Pattern 5: Checking Local Ollama Availability
**What:** Verify local Ollama is running and has required models
**When to use:** Startup health check, before local fallback
**Example:**
```python
import subprocess
from ollama import Client, ResponseError

def check_local_ollama(required_models=None):
    try:
        # Method 1: Try to list models via API
        client = Client(host='http://localhost:11434')
        models = client.list()
        available = [m['name'] for m in models['models']]

        if required_models:
            missing = set(required_models) - set(available)
            if missing:
                return False, f"Missing models: {missing}. Run: ollama pull {' '.join(missing)}"

        return True, "Ollama running with required models"

    except Exception as e:
        return False, f"Ollama not running. Start with: ollama serve"

def get_largest_available_model(models_list):
    """Select largest model from list based on parameter count"""
    # Model name format: model:size (e.g., gemma2:9b, llama3.2:3b)
    # Extract size and convert to numeric for comparison
    import re

    def extract_params(model_name):
        # Extract parameter count: "9b" -> 9000000000
        match = re.search(r'(\d+)b', model_name.lower())
        if match:
            return int(match.group(1)) * 1_000_000_000
        return 0

    return max(models_list, key=extract_params)
```

### Anti-Patterns to Avoid
- **Circuit breaker pattern:** User decided against this - always try cloud on each request for simpler, self-healing behavior
- **Exponential backoff:** User specified fixed delay for predictability and configuration simplicity
- **Soft limits:** Don't pre-emptively switch to local before hitting actual cloud quota - use cloud until 429 received
- **Auto-starting Ollama:** Default to failing with clear instructions rather than subprocess management complexity

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic | Custom for/while loop with sleep | `tenacity` decorators | Handles edge cases (async, exceptions, stop conditions), composable, tested |
| Request queueing | JSON file + custom reader | `persist-queue.SQLiteAckQueue` | Thread-safe, crash-resistant, acknowledgment pattern built-in |
| HTTP timeouts | Basic `timeout=X` | `httpx.Timeout(connect=5, read=90, write=10, pool=20)` | Granular control prevents wrong timeout type causing issues |
| Configuration | Custom .ini parser | `tomllib` (Python 3.11+) + env overrides | Standard library, human-readable TOML format |
| Structured logging | String formatting + print | `structlog` | Machine-readable, context propagation, integrates with observability tools |
| Model parameter parsing | String splitting | Regex with fallback + `max(key=fn)` | Handles variations in model naming (9b, 9B, 9-billion) |

**Key insight:** Error handling and retry logic have subtle failure modes (connection errors vs timeouts vs rate limits). Well-tested libraries prevent production surprises.

## Common Pitfalls

### Pitfall 1: Not Distinguishing Rate Limits from Other Errors
**What goes wrong:** Treating all errors the same causes unnecessary cooldowns or missing quota exhaustion
**Why it happens:** Status code 429 looks like just another error without special handling
**How to avoid:** Explicitly check `e.status_code == 429` and trigger 10-minute cooldown only for rate limits
**Warning signs:** Cloud quota "resets" but fallback still uses local; users hit quota but no warning logged

### Pitfall 2: Timeout Misconfiguration
**What goes wrong:** Connection timeout set to 90s causes 3-minute wait on network failures before fallback
**Why it happens:** Using single timeout value instead of granular connect/read/write timeouts
**How to avoid:** Set `httpx.Timeout(connect=5.0, read=90.0, write=10.0)` - fast connection failure, long read for LLM generation
**Warning signs:** Failover takes minutes instead of seconds; users report "hanging" requests

### Pitfall 3: Assuming Local Models Are Pulled
**What goes wrong:** Fallback fails with cryptic "model not found" error instead of clear instructions
**Why it happens:** Code assumes `ollama pull` already ran for required models
**How to avoid:** On startup or first local fallback, call `client.list()` and check for required models, fail with "Run: ollama pull model-name"
**Warning signs:** Users get `ResponseError` 404 instead of helpful error message

### Pitfall 4: Not Handling Streaming Errors Mid-Response
**What goes wrong:** Error occurs during streaming response, but HTTP status already sent as 200
**Why it happens:** Ollama sends errors as NDJSON `{"error": "..."}` objects during stream, status code doesn't change
**How to avoid:** When `stream=True`, check each yielded object for `'error'` key and raise immediately
**Warning signs:** Partial responses returned without error; logs show errors but callers don't see them

### Pitfall 5: Cooldown State Lost on Restart
**What goes wrong:** Application restarts during 10-minute cooldown, immediately retries cloud, hits rate limit again
**Why it happens:** Cooldown stored in memory (`self.cloud_cooldown_until`) not persisted
**How to avoid:** Store cooldown timestamp in SQLite or file (e.g., `~/.graphiti/llm_state.json`), load on init
**Warning signs:** Repeated rate-limit errors in logs after restarts; quota exhausted faster than expected

### Pitfall 6: Quantization Confusion
**What goes wrong:** Local models perform poorly compared to cloud, users blame implementation not model choice
**Why it happens:** Ollama defaults to quantized models (8-bit) for compatibility, sacrificing quality
**How to avoid:** Document model selection, consider defaulting to higher-precision variants when RAM/VRAM allows
**Warning signs:** Users report "local fallback gives wrong answers"; quality degrades noticeably on fallback

### Pitfall 7: Missing Model in Fallback Chain
**What goes wrong:** Fallback chain lists 3 models, first 2 aren't pulled, third fails, entire operation fails
**Why it happens:** Checking models at startup but not handling partial availability
**How to avoid:** Filter fallback chain to only pulled models at startup; warn about missing models but continue
**Warning signs:** Fallback works sometimes but not others; depends on which models user happened to pull

### Pitfall 8: Queue Grows Unbounded
**What goes wrong:** Network down for hours, queue fills disk, application crashes
**Why it happens:** No max queue size or TTL for queued requests
**How to avoid:** Set queue max size (e.g., 1000 items), add timestamp to requests, skip items older than 24h
**Warning signs:** Disk space alerts; queue processing takes hours after network restoration

## Code Examples

### Retry with Tenacity (Fixed Delay)
```python
# Source: https://tenacity.readthedocs.io/
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from ollama import ResponseError
import logging

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),  # 1 initial + 2 retries
    wait=wait_fixed(10),  # 10 seconds between attempts
    retry=retry_if_exception_type((ConnectionError, ResponseError)),
    before_sleep=lambda retry_state: logger.info(f"Retry {retry_state.attempt_number}/3 after 10s")
)
def call_cloud_ollama(client, model, messages):
    """Call cloud Ollama with automatic retry on errors"""
    return client.chat(model=model, messages=messages)
```

### Checking Response Headers for Quota
```python
# Source: Pattern from Ollama API research
# Note: Actual header names may vary - verify in production

def extract_quota_info(response):
    """Extract quota information from response headers if available"""
    # httpx Response object from ollama client
    headers = response.headers if hasattr(response, 'headers') else {}

    quota_info = {
        'limit': headers.get('x-ratelimit-limit'),
        'remaining': headers.get('x-ratelimit-remaining'),
        'reset': headers.get('x-ratelimit-reset'),  # Unix timestamp
    }

    if all(quota_info.values()):
        quota_info['usage_percent'] = (
            1 - int(quota_info['remaining']) / int(quota_info['limit'])
        ) * 100
        return quota_info

    return None  # Headers not available, use local counting
```

### Structured Logging for Failover Events
```python
# Source: https://www.structlog.org/
import structlog

logger = structlog.get_logger()

def log_failover_event(from_provider, to_provider, reason, error_code=None):
    """Log failover with structured data for observability"""
    logger.warning(
        "llm_failover",
        from_provider=from_provider,
        to_provider=to_provider,
        reason=reason,
        error_code=error_code,
        timestamp=time.time()
    )
    # Output (JSON): {"event": "llm_failover", "from_provider": "cloud",
    #                 "to_provider": "local", "reason": "rate_limit",
    #                 "error_code": 429, "timestamp": 1738703234.5}
```

### Queue-and-Raise Pattern
```python
# Source: User requirement from CONTEXT.md
from persist_queue import SQLiteAckQueue
import uuid

class LLMUnavailableError(Exception):
    """Raised when LLM request fails and is queued for retry"""
    def __init__(self, message, request_id):
        super().__init__(message)
        self.request_id = request_id

def call_with_queue_fallback(operation, params, queue):
    """Call LLM operation, queue and raise if both cloud and local fail"""
    try:
        # Try cloud then local (failover logic)
        return perform_llm_operation(operation, params)
    except Exception as e:
        # Both failed - queue for later
        request_id = str(uuid.uuid4())
        queue.put({
            'id': request_id,
            'operation': operation,
            'params': params,
            'timestamp': time.time(),
            'original_error': str(e)
        })

        raise LLMUnavailableError(
            f"LLM unavailable. Request queued for retry. ID: {request_id}",
            request_id=request_id
        )
```

### HTTPX Timeout Configuration for Ollama
```python
# Source: https://www.python-httpx.org/advanced/timeouts/
from ollama import Client
import httpx

# Configure granular timeouts
timeout_config = httpx.Timeout(
    connect=5.0,   # Fast fail on connection issues
    read=90.0,     # Allow long reads for LLM generation
    write=10.0,    # Moderate write timeout
    pool=20.0      # Connection pool acquisition timeout
)

# Cloud client with authentication
cloud_client = Client(
    host='https://ollama.com',
    headers={'Authorization': f'Bearer {api_key}'},
    timeout=timeout_config
)

# Local client (no auth, shorter read timeout acceptable)
local_timeout = httpx.Timeout(connect=2.0, read=60.0, write=10.0, pool=5.0)
local_client = Client(
    host='http://localhost:11434',
    timeout=local_timeout
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Local-only Ollama | Cloud + local hybrid | Q4 2025 - Q1 2026 | Cloud models (120B params) available without high-end GPU |
| Manual model switching | Automatic failover | 2026 | Graceful degradation, better UX |
| Requests library | httpx | 2023+ | Async support, better timeout control, HTTP/2 |
| String format logging | Structured logging (JSON) | 2024+ | Better observability, easier log aggregation |
| .env files | TOML configuration | 2025+ | Type-safe, standardized (Python 3.11+ stdlib) |

**Deprecated/outdated:**
- `retrying` library: Unmaintained since 2016, use `tenacity` instead (actively maintained)
- `urllib3.Retry` with `requests.adapters.HTTPAdapter`: Works but less flexible than tenacity for non-HTTP retries
- Global logging configuration: Modern apps use `structlog` with context binding

## Open Questions

### 1. Actual Quota Headers from Ollama Cloud
- **What we know:** Standard rate-limiting uses `X-RateLimit-*` headers (429 status confirmed in docs)
- **What's unclear:** Exact header names Ollama cloud uses (`X-RateLimit-Remaining` vs `X-Rate-Limit-Remaining` vs custom)
- **Recommendation:** Implement both header-based and local-counting quota tracking. At runtime, log response headers on first cloud call to verify. Fall back to counting if headers unavailable.

### 2. Default Local Model Selection Strategy
- **What we know:** User wants "largest-param model available" as default. Models named like `gemma2:9b`, `llama3.2:3b`
- **What's unclear:** How to reliably extract param count from various naming schemes (9b vs 9B vs 9-billion vs unstated)
- **Recommendation:** Use regex to extract number + suffix (b/B), convert to billions, sort descending. If extraction fails for a model, assign it lowest priority (0 params). Document supported naming patterns.

### 3. Queue Retry Scheduling
- **What we know:** Failed requests queued for later processing
- **What's unclear:** When/how to retry queued requests (background thread? CLI command? Next API call?)
- **Recommendation:** Implement both: (1) Background thread that attempts queue processing every 5 minutes if items exist, (2) `graphiti retry-queue` CLI command for manual triggering. Add queue status to `graphiti quota` command.

### 4. Cooldown Persistence
- **What we know:** 10-minute cooldown after rate limit (429)
- **What's unclear:** Whether to persist cooldown across application restarts
- **Recommendation:** Persist to avoid immediately re-hitting rate limit. Store in `~/.graphiti/llm_state.json` with `{"cloud_cooldown_until": <unix_timestamp>}`. Load on init.

### 5. Local Ollama Auto-Start Decision
- **What we know:** User decided default OFF, fail with instructions
- **What's unclear:** Configuration option to enable auto-start for advanced users?
- **Recommendation:** Provide `local.auto_start = false` config option (default off). If true and Ollama not running, attempt `subprocess.Popen(['ollama', 'serve'], ...)`. Document risks (subprocess management, port conflicts).

## Sources

### Primary (HIGH confidence)
- [Ollama Python library v0.6.1](https://github.com/ollama/ollama-python) - Error handling, API methods, configuration
- [Ollama API Documentation - Authentication](https://docs.ollama.com/api/authentication) - API key, environment variables
- [Ollama API Documentation - Errors](https://docs.ollama.com/api/errors) - Status codes, error response format
- [Ollama Cloud Documentation](https://docs.ollama.com/cloud) - Cloud service, authentication requirements
- [Ollama Pricing](https://ollama.com/pricing) - Pricing tiers, usage limits
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Retry patterns, decorators, configuration
- [HTTPX Timeouts Documentation](https://www.python-httpx.org/advanced/timeouts/) - Timeout configuration
- [persist-queue v1.1.0 PyPI](https://pypi.org/project/persist-queue/) - Queue features, acknowledgment pattern

### Secondary (MEDIUM confidence)
- [Complete Ollama Tutorial (2026) - DEV Community](https://dev.to/proflead/complete-ollama-tutorial-2026-llms-via-cli-cloud-python-3m97) - Verified with official docs
- [Ollama models library](https://ollama.com/library) - Model specifications (gemma2, llama3.2, nomic-embed-text)
- [Python Logging Best Practices 2026 - Better Stack](https://betterstack.com/community/guides/logging/python/python-logging-best-practices/) - Structured logging patterns
- [Dynaconf Documentation](https://www.dynaconf.com/) - TOML + environment variable configuration
- [Python Requests Retry 2026 - ZenRows](https://www.zenrows.com/blog/python-requests-retry) - Retry best practices
- [RQ Exception & Retry Documentation](https://python-rq.org/docs/exceptions/) - Queue retry patterns

### Tertiary (LOW confidence)
- [Common Ollama Integration Mistakes - Medium](https://sebastianpdw.medium.com/common-mistakes-in-local-llm-deployments-03e7d574256b) - Pitfalls (quantization, context windows)
- [Fallback Pattern for AI Providers - Medium](https://medium.com/flux-it-thoughts/fallback-the-contingency-plan-when-your-ai-provider-fails-7faf01a26a6d) - Fallback architecture pattern
- [5 Ollama Integration Mistakes - Dre Dyson](https://dredyson.com/5-ollama-integration-mistakes-that-compromise-local-ai-privacy-and-how-to-avoid-them/) - Security/privacy pitfalls

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official ollama library confirmed, version verified, tenacity is industry standard
- Architecture: HIGH - Patterns verified from official docs and established best practices
- Pitfalls: MEDIUM - Derived from community issues and Ollama GitHub issues, verified where possible

**Research date:** 2026-02-04
**Valid until:** 2026-03-06 (30 days - Ollama cloud is new but API should be stable)

**Notes:**
- Ollama cloud launched in late 2025/early 2026, still in preview
- Quota header names need runtime verification (documented in Open Questions)
- Python 3.11+ required for `tomllib` (stdlib TOML parser)
- All user decisions from CONTEXT.md incorporated (no circuit breaker, fixed delay, configurable defaults, etc.)
