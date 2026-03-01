# Phase 5: Background Queue - Research

**Researched:** 2026-02-12
**Domain:** Python background worker threads, SQLite-backed persistent queues, async job processing
**Confidence:** HIGH

## Summary

Phase 5 implements an async processing queue infrastructure to enable non-blocking operations for Claude Code hooks and future conversation capture. The queue uses SQLite for persistence with acknowledgment patterns (ack/nack), runs a background worker thread inside the MCP server process, and provides CLI fallback for manual processing. The architecture follows the established pattern from Phase 3 (LLMRequestQueue) but extends it to support parallel job batching, sequential barriers, exponential backoff retry, and dead letter queue handling.

Python's `threading` module with `threading.Event` for graceful shutdown, `persistqueue.SQLiteAckQueue` for persistent storage, and `concurrent.futures.ThreadPoolExecutor` for parallel batch processing provide the standard stack. The key architectural decision is running workers as background threads within the MCP server process (not separate processes or async tasks), ensuring jobs are processed while Claude Code is active. Hook context auto-detection via environment variables enables silent queueing during hooks vs. explicit feedback during interactive CLI use.

**Primary recommendation:** Extend existing LLMRequestQueue pattern with custom SQLite schema for job metadata (job_type, parallel flag, status, attempts), use threading.Event for worker lifecycle control, implement ThreadPoolExecutor for parallel batches, and add dead letter table for failed jobs after 3 retries with exponential backoff (10s, 20s, 40s).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Queue Architecture:**
- Primary worker runs as background thread inside MCP server process
- CLI fallback command (`graphiti process-queue` or similar) for manual processing when MCP isn't running
- Global FIFO with parallel batching: single queue ordered by timestamp
  - Sequential jobs act as barriers — process alone, wait until done
  - Consecutive parallel jobs batch together — run concurrently
  - Jobs carry a `parallel: bool` flag set by the caller at enqueue time
- Custom SQLite table (same DB pattern as Phase 3): id, created_at, parallel flag, job_type, payload, status, attempts
- Conditional eager startup: on MCP boot, check if backlog exists — start workers if yes, wait if no

**Job Submission API:**
- Dual submission mode: `--async` flag for explicit async + auto-detect hook context
  - Claude Code hooks: auto-detected, always queues (silent)
  - Interactive CLI: processes synchronously by default, `--async` to explicitly queue
- Minimal payload: store CLI command + arguments, worker replays the command
- Context-aware feedback: silent for auto-detected hooks, one-liner confirmation for explicit `--async`
- Queue inspection via `graphiti queue status` command for viewing pending/processing/failed jobs

**Failure Handling:**
- 3 retries before giving up
- Exponential backoff between retries (10s, 20s, 40s)
- Dead jobs move to dead letter table — preserved for inspection, can be manually retried
- Full isolation: each job fails independently, never blocks or affects other jobs

**Backpressure Handling:**
- Soft limit: always accept jobs, never lose knowledge, log warnings when queue exceeds threshold
- Queue size configurable (default 100), soft cap not hard rejection
- `graphiti queue status` shows warning at 80% capacity, error at 100%+ (same pattern as health check)
- No data loss guarantee: jobs always accepted regardless of queue size

### Claude's Discretion

- Thread pool size for parallel batch processing
- SQLite table schema details and indexing
- Auto-detection mechanism for hook context vs interactive CLI
- Dead letter table schema and manual retry UX
- Worker thread shutdown/cleanup on MCP server stop

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| threading | stdlib | Background worker lifecycle, Event for shutdown | Built-in, battle-tested, official Python threading primitives |
| concurrent.futures | stdlib | ThreadPoolExecutor for parallel batch processing | Official high-level interface, maintains worker pool, handles task scheduling |
| persistqueue | 1.1.0 | SQLiteAckQueue for persistent job storage with ack/nack | Already in use (Phase 3), proven crash-resistant, ack pattern matches retry needs |
| sqlite3 | stdlib | Database connection management, custom schema | Native SQLite support, transaction control, thread-safe with proper connection management |
| structlog | 25.5.0+ | Structured logging for queue events | Already in use, provides context-rich logs for debugging queue behavior |
| time | stdlib | Timestamp generation, sleep for backoff delays | Standard time operations, no dependencies |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid | stdlib | Job ID generation | Unique identifiers for tracking individual jobs |
| json | stdlib | Serialize/deserialize job payloads | Store CLI command + arguments as JSON in SQLite TEXT column |
| os | stdlib | Environment variable detection for hook context | Check for Claude Code environment markers |
| sys | stdlib | TTY detection (stdin.isatty()) | Distinguish interactive CLI from hook invocation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| threading | asyncio | asyncio requires async/await throughout codebase; threading integrates with sync CLI without refactoring |
| ThreadPoolExecutor | multiprocessing.Pool | Multiprocessing has higher overhead, slower startup, serialization costs; threads sufficient for I/O-bound CLI replay |
| persistqueue | Custom SQLite | Custom solution loses crash recovery, ack/nack patterns, battle-tested persistence; persistqueue provides these out-of-box |
| In-process worker | Separate daemon process | Daemon process adds complexity (lifecycle management, IPC, process supervision); in-process worker simpler and guaranteed available when MCP runs |

**Installation:**

Already installed (no new dependencies):
```bash
# All required packages already in pyproject.toml
# persistqueue==1.1.0
# structlog>=25.5.0
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── queue/                    # Background queue system (NEW)
│   ├── __init__.py          # Public API: enqueue, get_status, process_queue
│   ├── models.py            # QueuedJob dataclass, JobStatus enum, QueueStats
│   ├── storage.py           # JobQueue class with SQLite schema, ack/nack
│   ├── worker.py            # BackgroundWorker thread with Event lifecycle
│   └── detector.py          # Context detection (hook vs interactive)
├── cli/                     # CLI commands
│   ├── commands/
│   │   └── queue.py         # NEW: graphiti queue status/process/retry commands
│   └── utils.py             # Hook detection helper
└── mcp/                     # MCP server (Phase 8, but worker starts here)
    └── server.py            # Worker startup on MCP boot
```

### Pattern 1: Background Worker with Event-Based Shutdown

**What:** Dedicated background thread that processes queue items until signaled to stop via threading.Event. Worker polls queue, processes batch of jobs, sleeps briefly, then checks stop signal.

**When to use:** Long-running background processing that must shutdown gracefully without data loss.

**Example:**
```python
# Source: https://superfastpython.com/threading-in-python/index (adapted)
from threading import Thread, Event
from time import sleep

class BackgroundWorker:
    def __init__(self, job_queue, stop_event):
        self._queue = job_queue
        self._stop_event = stop_event
        self._thread = None

    def start(self):
        """Start worker thread if not already running."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = Thread(target=self._run, daemon=False)
            self._thread.start()

    def stop(self, timeout=30):
        """Signal worker to stop and wait for clean shutdown."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout)

    def _run(self):
        """Main worker loop - processes jobs until stopped."""
        while not self._stop_event.is_set():
            # Process batch of jobs
            processed = self._queue.process_batch()

            # Sleep briefly or wait for stop signal (responsive shutdown)
            if not processed:
                self._stop_event.wait(timeout=1.0)  # Wake on stop or after 1s
```

### Pattern 2: SQLite Queue with Custom Schema and Ack Pattern

**What:** Extend persistqueue.SQLiteAckQueue with custom schema for job metadata (status, attempts, parallel flag). Use ack() to remove completed jobs, nack() to requeue failed jobs, custom table for dead letters.

**When to use:** Persistent job queues that need retry logic, job metadata, and crash recovery.

**Example:**
```python
# Adapted from existing src/llm/queue.py pattern
from persistqueue import SQLiteAckQueue
from dataclasses import dataclass, asdict
import time
import json

@dataclass
class QueuedJob:
    id: str
    job_type: str        # e.g., "add_knowledge", "capture_commit"
    payload: dict        # CLI command + args as dict
    parallel: bool       # Can run in parallel batch
    timestamp: float
    status: str          # "pending", "processing", "failed"
    attempts: int
    last_error: str | None

class JobQueue:
    def __init__(self, db_path, max_size=100):
        self._queue = SQLiteAckQueue(db_path, auto_commit=True)
        self._max_size = max_size
        self._init_custom_schema()  # Add job metadata columns

    def enqueue(self, job_type, payload, parallel=False):
        """Add job to queue, prune if at capacity."""
        if self._queue.qsize() >= self._max_size:
            self._prune_oldest()

        job = QueuedJob(
            id=str(uuid.uuid4()),
            job_type=job_type,
            payload=payload,
            parallel=parallel,
            timestamp=time.time(),
            status="pending",
            attempts=0,
            last_error=None
        )
        self._queue.put(asdict(job))
        return job.id

    def get_batch(self, max_items=10):
        """Get batch of consecutive parallel or single sequential job."""
        batch = []
        first_item = self._queue.get(block=False) if self._queue.qsize() > 0 else None

        if first_item is None:
            return []

        batch.append(first_item)

        # If first job is sequential, return only it (barrier)
        if not first_item['parallel']:
            return batch

        # Collect consecutive parallel jobs
        while len(batch) < max_items and self._queue.qsize() > 0:
            item = self._queue.get(block=False)
            if item['parallel']:
                batch.append(item)
            else:
                # Sequential job encountered - requeue it, stop batch
                self._queue.nack(item)
                break

        return batch

    def ack(self, job):
        """Mark job as successfully completed."""
        self._queue.ack(job)

    def nack(self, job):
        """Requeue job for retry."""
        job['attempts'] += 1
        self._queue.nack(job)

    def move_to_dead_letter(self, job):
        """Move failed job to dead letter table after max retries."""
        # Custom SQLite insert into dead_letter_jobs table
        pass
```

### Pattern 3: Parallel Batch Processing with ThreadPoolExecutor

**What:** Use ThreadPoolExecutor to process parallel jobs concurrently. Submit batch of jobs, wait for completion, handle individual failures gracefully.

**When to use:** I/O-bound tasks (CLI command replay) that can run concurrently without blocking each other.

**Example:**
```python
# Source: https://docs.python.org/3/library/concurrent.futures.html (adapted)
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_batch(jobs, executor, max_workers=4):
    """Process batch of parallel jobs concurrently."""
    futures = {executor.submit(replay_command, job): job for job in jobs}

    results = []
    for future in as_completed(futures):
        job = futures[future]
        try:
            result = future.result()
            results.append(("success", job, result))
        except Exception as e:
            results.append(("failure", job, str(e)))

    return results

def replay_command(job):
    """Execute CLI command from job payload."""
    # Reconstruct CLI command from job['payload']
    # Use subprocess or direct function call
    pass
```

### Pattern 4: Hook Context Detection

**What:** Detect if code is running in Claude Code hook context vs. interactive CLI by checking environment variables and TTY status.

**When to use:** Provide different feedback (silent vs. verbose) based on invocation context.

**Example:**
```python
import os
import sys

def is_hook_context() -> bool:
    """Detect if running in Claude Code hook context.

    Returns:
        True if in hook context (should be silent), False if interactive CLI
    """
    # Check for Claude Code environment markers
    # Source: https://code.claude.com/docs/en/mcp (environment variables passed to hooks)
    if any(key.startswith("CLAUDE_") for key in os.environ):
        return True

    # Check if stdin is a TTY (interactive terminal)
    if not sys.stdin.isatty():
        return True

    return False

def enqueue_with_feedback(job_type, payload, parallel=False):
    """Enqueue job with context-aware feedback."""
    job_id = queue.enqueue(job_type, payload, parallel)

    if is_hook_context():
        # Silent - no output during hooks
        pass
    else:
        # Interactive - provide confirmation
        print(f"Job queued: {job_id}")

    return job_id
```

### Pattern 5: Exponential Backoff Retry

**What:** Retry failed jobs with exponentially increasing delays (10s, 20s, 40s). Track attempts in job metadata, move to dead letter after max retries.

**When to use:** Transient failures (network issues, temporary resource unavailability) that may succeed on retry.

**Example:**
```python
import time

def calculate_backoff_delay(attempt):
    """Calculate exponential backoff delay.

    Args:
        attempt: Retry attempt number (0-indexed)

    Returns:
        Delay in seconds (10, 20, 40)
    """
    base_delay = 10  # seconds
    return base_delay * (2 ** attempt)

def process_with_retry(job, max_retries=3):
    """Process job with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            result = replay_command(job)
            return ("success", result)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = calculate_backoff_delay(attempt)
                logger.warning(
                    "job_failed_retrying",
                    job_id=job['id'],
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_seconds=delay,
                    error=str(e)
                )
                time.sleep(delay)
            else:
                # Max retries exceeded - move to dead letter
                logger.error(
                    "job_failed_max_retries",
                    job_id=job['id'],
                    max_retries=max_retries,
                    error=str(e)
                )
                return ("dead_letter", e)

    return ("failure", "Unexpected retry loop exit")
```

### Anti-Patterns to Avoid

- **Daemon threads for workers:** Non-daemon threads ensure graceful shutdown. Daemon threads are killed abruptly on exit, losing in-progress jobs.
- **Single connection shared across threads:** SQLite connections are not thread-safe. Use connection-per-thread pattern or single-threaded queue access.
- **Infinite retry loops:** Always limit retries to prevent resource exhaustion. Move failed jobs to dead letter after max attempts.
- **Blocking the main thread:** Worker must run in background thread. Never call `thread.join()` in main execution path except during shutdown.
- **check_same_thread=False:** Disabling SQLite's thread check hides problems. Use proper connection management instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Persistent queue with crash recovery | Custom SQLite queue implementation | persistqueue.SQLiteAckQueue | Handles ack/nack patterns, crash recovery, auto-commit, blocking/non-blocking get, proven in production |
| Thread pool management | Manual thread creation and lifecycle | concurrent.futures.ThreadPoolExecutor | Handles worker pool sizing, task scheduling, exception capture, graceful shutdown |
| Worker shutdown signaling | Custom flags or polling | threading.Event | Built-in, efficient wait/notify pattern, prevents busy-waiting, integrates with thread lifecycle |
| Structured logging | String concatenation or print statements | structlog | Context propagation, JSON output, log levels, integration with monitoring systems |
| Job ID generation | Timestamp-based or sequential IDs | uuid.uuid4() | Guaranteed uniqueness across processes, no coordination needed, URL-safe |

**Key insight:** Background queue processing has well-established patterns in Python stdlib and mature libraries. Custom solutions introduce bugs (race conditions, deadlocks, memory leaks) that take months to surface. Use proven primitives and patterns.

## Common Pitfalls

### Pitfall 1: SQLite Connection Thread Safety

**What goes wrong:** Using single SQLite connection from multiple threads causes "SQLite objects created in a thread can only be used in that same thread" errors.

**Why it happens:** SQLite's default `check_same_thread=True` prevents cross-thread connection use to avoid corruption. Even with `check_same_thread=False`, concurrent writes can corrupt database.

**How to avoid:**
- Use persistqueue's SQLiteAckQueue which handles thread-safety internally
- For custom queries, create connection per thread using threading.local()
- Enable WAL mode for better read concurrency
- Single writer thread pattern (all writes go through queue worker)

**Warning signs:**
- ProgrammingError mentioning thread IDs
- Database locked errors under concurrent access
- Silent data corruption (missing or duplicate jobs)

**Sources:**
- [Python, SQLite, and thread safety](https://ricardoanderegg.com/posts/python-sqlite-thread-safety/)
- [How to Use SQLite in Python Applications](https://oneuptime.com/blog/post/2026-02-02-sqlite-python/view)

### Pitfall 2: Worker Thread Not Joining on Shutdown

**What goes wrong:** Using daemon threads for workers or failing to call `thread.join()` on shutdown causes in-progress jobs to be lost when process exits.

**Why it happens:** Python exits immediately after main thread completes, killing daemon threads mid-execution. Non-daemon threads without proper join cause hanging processes.

**How to avoid:**
- Use non-daemon threads for workers
- Implement threading.Event for shutdown signaling
- Call `stop_event.set()` then `thread.join(timeout)` on shutdown
- Handle timeout gracefully (log warning, force exit if needed)

**Warning signs:**
- Jobs disappear from queue without completion
- Process hangs on exit (SIGTERM doesn't work)
- "Thread still running" warnings in logs

**Sources:**
- [SuperFastPython: Stopping a Thread Gracefully](https://superfastpython.com/threading-in-python/index)
- [How to stop a Python thread cleanly](https://alexandra-zaharia.github.io/posts/how-to-stop-a-python-thread-cleanly/)

### Pitfall 3: Memory Leaks from Unbounded Queue Growth

**What goes wrong:** Queue grows unbounded during high load or worker downtime, consuming all available memory and eventually crashing.

**Why it happens:** Always accepting jobs without backpressure leads to queue growth faster than processing rate during spikes.

**How to avoid:**
- Enforce max queue size (default 100 per requirements)
- Prune oldest items when at capacity (soft limit, never reject)
- Log warnings at 80% capacity, errors at 100%+
- Monitor queue size metrics in health check

**Warning signs:**
- Increasing memory usage over time
- OOM kills in production
- Queue size continuously growing in metrics

**Sources:**
- Existing Phase 3 implementation in src/llm/queue.py (bounded queue pattern)

### Pitfall 4: Race Conditions in Parallel Batch Processing

**What goes wrong:** Parallel jobs modify shared state (database, files) causing corruption or lost updates.

**Why it happens:** ThreadPoolExecutor runs jobs concurrently without synchronization. If jobs aren't truly independent, race conditions occur.

**How to avoid:**
- Ensure parallel jobs are truly independent (no shared mutable state)
- Use locks or transactions for shared resource access
- Validate parallel=True flag is only set for safe operations
- Test with high concurrency (100+ parallel jobs)

**Warning signs:**
- Intermittent test failures
- Corrupted database entries
- Lost updates (last write wins)

**Sources:**
- [concurrent.futures documentation](https://docs.python.org/3/library/concurrent.futures.html)

### Pitfall 5: Not Handling CLI Command Replay Failures Gracefully

**What goes wrong:** Worker crashes when replaying CLI command that has invalid arguments or missing dependencies.

**Why it happens:** Job payload stored at enqueue time may reference files/state that no longer exists at replay time.

**How to avoid:**
- Wrap command replay in try/except with specific error handling
- Validate payload structure before replay
- Log detailed error context (command, args, exception)
- Move to dead letter after retries (don't crash worker)

**Warning signs:**
- Worker thread exits unexpectedly
- Same job fails repeatedly with different errors
- No jobs processed after worker crash

**Sources:**
- Pattern established in Phase 3 LLMRequestQueue error handling

## Code Examples

Verified patterns from official sources and existing codebase:

### Worker Lifecycle with Event-Based Shutdown

```python
# Source: https://superfastpython.com/threading-in-python/index + Phase 3 patterns
from threading import Thread, Event
import structlog

logger = structlog.get_logger()

class BackgroundWorker:
    """Background worker thread for processing queue jobs.

    Runs continuously until signaled to stop via Event. Non-daemon thread
    ensures graceful shutdown with job completion.
    """

    def __init__(self, job_queue):
        self._queue = job_queue
        self._stop_event = Event()
        self._thread = None
        self._executor = None

    def start(self):
        """Start worker thread if backlog exists or on first job."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = Thread(target=self._run, daemon=False)
            self._thread.start()
            logger.info("background_worker_started")

    def stop(self, timeout=30):
        """Signal worker to stop and wait for clean shutdown."""
        if self._thread and self._thread.is_alive():
            logger.info("background_worker_stopping")
            self._stop_event.set()
            self._thread.join(timeout)

            if self._thread.is_alive():
                logger.warning(
                    "background_worker_timeout",
                    timeout_seconds=timeout
                )
            else:
                logger.info("background_worker_stopped")

    def _run(self):
        """Main worker loop."""
        # Create thread pool for parallel batches
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=4)

        try:
            while not self._stop_event.is_set():
                # Get batch of jobs (parallel or single sequential)
                batch = self._queue.get_batch(max_items=10)

                if not batch:
                    # No jobs - wait briefly or until stopped
                    self._stop_event.wait(timeout=1.0)
                    continue

                # Process batch
                self._process_batch(batch)

        finally:
            # Cleanup thread pool
            self._executor.shutdown(wait=True)
            logger.info("background_worker_shutdown_complete")

    def _process_batch(self, batch):
        """Process batch of jobs (parallel or sequential)."""
        if len(batch) == 1 and not batch[0]['parallel']:
            # Sequential job - process alone
            self._process_job(batch[0])
        else:
            # Parallel batch - process concurrently
            self._process_parallel_batch(batch)

    def _process_job(self, job):
        """Process single job with retry logic."""
        # Implementation with exponential backoff
        pass

    def _process_parallel_batch(self, jobs):
        """Process batch of parallel jobs concurrently."""
        # Use self._executor to run jobs in parallel
        pass
```

### Queue Status Command (CLI)

```python
# Pattern similar to src/cli/commands/health.py
import typer
from rich.console import Console
from rich.table import Table

def queue_status():
    """Display queue status with health indicators.

    Shows pending/processing/failed jobs with color-coded warnings:
    - Green (ok): < 80 items
    - Yellow (warning): 80-99 items
    - Red (error): 100+ items
    """
    from src.queue import get_queue_stats

    stats = get_queue_stats()
    console = Console()

    # Determine health status
    pending = stats['pending']
    max_size = stats['max_size']

    if pending >= max_size:
        status = "[red]ERROR[/red]"
        message = "Queue at capacity"
    elif pending >= max_size * 0.8:
        status = "[yellow]WARNING[/yellow]"
        message = "Queue nearly full"
    else:
        status = "[green]OK[/green]"
        message = "Queue healthy"

    # Display table
    table = Table(title="Queue Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Status", status)
    table.add_row("Pending Jobs", str(pending))
    table.add_row("Capacity", f"{pending}/{max_size}")
    table.add_row("Failed (Dead Letter)", str(stats.get('dead_letter', 0)))
    table.add_row("Message", message)

    console.print(table)
```

### Hook Context Detection

```python
# Based on Claude Code documentation and TTY detection patterns
import os
import sys

def is_hook_context() -> bool:
    """Detect if running in Claude Code hook context.

    Returns:
        True if in hook (silent mode), False if interactive CLI
    """
    # Check for Claude Code environment variables
    # Source: https://code.claude.com/docs/en/mcp
    if any(key.startswith("CLAUDE_") for key in os.environ):
        return True

    # Check if stdin is a TTY (interactive terminal)
    if not sys.stdin.isatty():
        return True

    # Check for common CI/CD environment markers
    ci_markers = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_HOME"]
    if any(marker in os.environ for marker in ci_markers):
        return True

    return False

def enqueue_with_context_aware_feedback(job_type, payload, parallel=False):
    """Enqueue job with appropriate feedback based on context."""
    from src.queue import enqueue
    import structlog

    job_id = enqueue(job_type, payload, parallel)

    if is_hook_context():
        # Silent - only structured log for debugging
        structlog.get_logger().debug(
            "job_queued_hook_context",
            job_id=job_id,
            job_type=job_type
        )
    else:
        # Interactive - user feedback
        print(f"✓ Job queued: {job_id}")

    return job_id
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| multiprocessing.Queue (in-memory) | persistqueue.SQLiteAckQueue | 2020+ | Crash recovery, job persistence across restarts, ack/nack patterns |
| Manual thread management | concurrent.futures.ThreadPoolExecutor | Python 3.2+ | Higher-level API, better exception handling, graceful shutdown |
| time.sleep() in worker loop | Event.wait(timeout) | Best practice | Responsive shutdown, no busy-waiting, cleaner code |
| daemon=True for background threads | daemon=False + Event shutdown | Best practice | Prevents job loss on exit, graceful completion |
| check_same_thread=False workaround | Connection-per-thread pattern | Always recommended | Prevents corruption, clearer thread safety model |

**Deprecated/outdated:**
- **Queue.Queue for persistent storage:** In-memory only, lost on crash. Use persistqueue for disk-backed queues.
- **threading.Thread.stop():** Never existed (common misconception). Use Event-based cooperative shutdown.
- **Global queue instance without lifecycle management:** Must start/stop worker thread explicitly. Use context manager or explicit start/stop.

## Open Questions

1. **Thread pool size for parallel batches**
   - What we know: ThreadPoolExecutor default is min(32, cpu_count() + 4) in Python 3.13+
   - What's unclear: Optimal size for CLI command replay workload (I/O-bound, not CPU-bound)
   - Recommendation: Start with 4 workers (testing can tune). CLI commands are fast (<1s typically), 4 provides good concurrency without overwhelming system. Configurable via env var.

2. **Worker startup trigger**
   - What we know: Should check backlog on MCP boot and start if jobs pending
   - What's unclear: Threshold for "backlog exists" (1 job? 10 jobs?)
   - Recommendation: Start on any pending job (threshold=1). Worker overhead is minimal, better to process jobs proactively than wait for more to accumulate.

3. **Dead letter table schema and retry UX**
   - What we know: Dead letter table stores failed jobs after 3 retries
   - What's unclear: Schema details (copy all columns? add failure metadata?), manual retry workflow
   - Recommendation: Mirror main queue schema + add fields: failed_at timestamp, final_error text, retry_count int. Manual retry via `graphiti queue retry <job_id>` command that moves job back to main queue with reset attempts.

4. **Hook environment variable for auto-detection**
   - What we know: Claude Code sets environment variables for hooks
   - What's unclear: Specific variable names to check for reliable detection
   - Recommendation: Check for any `CLAUDE_*` prefix as conservative approach. Test with actual Claude Code hook to verify. Fallback to TTY detection if no env vars found.

## Sources

### Primary (HIGH confidence)

- **Python Threading Documentation** - [SuperFastPython Threading Guide](https://superfastpython.com/threading-in-python/index) - Worker lifecycle, Event-based shutdown, daemon vs non-daemon threads
- **concurrent.futures Documentation** - [Official Python Docs](https://docs.python.org/3/library/concurrent.futures.html) - ThreadPoolExecutor patterns, batch processing, exception handling
- **persistqueue Package** - [PyPI: persist-queue](https://pypi.org/project/persist-queue/) - SQLiteAckQueue API, ack/nack patterns, thread safety
- **SQLite Thread Safety** - [Official SQLite Docs](https://www.sqlite.org/threadsafe.html) + [Python SQLite Thread Safety](https://ricardoanderegg.com/posts/python-sqlite-thread-safety/) - Connection management, WAL mode, check_same_thread
- **Existing codebase** - src/llm/queue.py (Phase 3) - Established patterns for queue operations, error handling, bounded queue

### Secondary (MEDIUM confidence)

- **SQLite Worker Libraries** - [Medium: SQLite Worker](https://medium.com/@roshanlamichhane/sqlite-worker-supercharge-your-sqlite-performance-in-multi-threaded-python-applications-01e2e43cc406) - Background worker patterns, performance characteristics
- **Python Graceful Shutdown** - [Alexandra Zaharia: Stop Thread Cleanly](https://alexandra-zaharia.github.io/posts/how-to-stop-a-python-thread-cleanly/) - Event-based shutdown patterns, best practices
- **MCP Server Integration** - [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp) - Environment variables, hook context, server lifecycle
- **Dead Letter Queue Patterns** - [OneUpTime: Dead Letter Queues in Python](https://oneuptime.com/blog/post/2026-01-24-dead-letter-queues-python/view) - DLQ patterns, retry strategies

### Tertiary (LOW confidence)

- **Python CLI Context Detection** - Web search results on argparse/click/typer - TTY detection approaches, interactive vs non-interactive modes (no specific 2026 updates found, marked for validation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries in use or stdlib, proven patterns from Phase 3
- Architecture: HIGH - Worker thread + SQLiteAckQueue pattern well-established, similar to existing LLMRequestQueue
- Pitfalls: HIGH - SQLite thread safety and worker lifecycle issues well-documented with clear solutions
- Hook detection: MEDIUM - Claude Code environment variables need validation with actual hook execution
- Thread pool sizing: MEDIUM - General guidance available, project-specific tuning needed

**Research date:** 2026-02-12
**Valid until:** 2026-03-12 (30 days - stable domain with mature libraries)
