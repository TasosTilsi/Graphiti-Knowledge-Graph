"""Background job queue package.

This package provides a persistent, SQLite-backed job queue for async processing
of CLI commands. Jobs can be queued during Claude Code hooks (silent mode) or
interactively (with feedback), then processed by background workers in the MCP server.

Key features:
- SQLite persistence: Jobs survive process restarts
- FIFO ordering: Oldest jobs processed first
- Parallel batching: Consecutive parallel jobs run concurrently
- Sequential barriers: Non-parallel jobs processed alone
- Dead letter queue: Failed jobs preserved for inspection
- Hook context detection: Auto-silent mode for hooks/CI/CD

Typical usage:
    from src.queue import QueuedJob, JobStatus, is_hook_context

    # Check context and enqueue job
    if is_hook_context():
        # Silent mode - no user output
        job_id = queue.enqueue("add_knowledge", payload, parallel=True)
    else:
        # Interactive - provide feedback
        job_id = queue.enqueue("add_knowledge", payload, parallel=True)
        print(f"Job queued: {job_id}")

Public API (added in Plan 02):
    - enqueue(): Add job to queue
    - get_status(): Get queue statistics
    - process_queue(): CLI fallback for manual processing
"""

from src.queue.models import (
    QueuedJob,
    JobStatus,
    QueueStats,
    DeadLetterJob,
)
from src.queue.detector import is_hook_context

__all__ = [
    "QueuedJob",
    "JobStatus",
    "QueueStats",
    "DeadLetterJob",
    "is_hook_context",
]
