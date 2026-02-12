"""Data models for background job queue.

This module defines the core data types for the persistent job queue system:
- Job status enum
- Queued job dataclass with metadata
- Dead letter job dataclass for failed jobs
- Queue statistics dataclass for health monitoring
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class JobStatus(Enum):
    """Job processing status.

    Attributes:
        PENDING: Job is queued, awaiting processing
        PROCESSING: Job is currently being executed
        FAILED: Job failed during execution (may retry)
        DEAD: Job exhausted all retries, moved to dead letter
    """
    PENDING = "pending"
    PROCESSING = "processing"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class QueuedJob:
    """A job queued for background processing.

    Jobs are persisted to SQLite and processed by background workers.
    The parallel flag determines batching behavior: parallel jobs can run
    concurrently, sequential jobs act as barriers.

    Attributes:
        id: Unique job identifier (UUID4 string)
        job_type: Job category (e.g., "add_knowledge", "capture_commit")
        payload: CLI command and arguments as dict (minimal payload)
        parallel: Whether job can run in parallel batch (caller sets at enqueue)
        created_at: Unix timestamp when job was created
        status: Current processing status
        attempts: Number of times job has been attempted
        last_error: Error message from most recent failure (if any)
    """
    id: str
    job_type: str
    payload: dict
    parallel: bool
    created_at: float = field(default_factory=time.time)
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    last_error: Optional[str] = None


@dataclass
class DeadLetterJob:
    """A job that exhausted all retries and moved to dead letter queue.

    Preserves all original job data plus failure metadata for inspection
    and potential manual retry.

    Attributes:
        id: Original job ID
        job_type: Original job category
        payload: Original CLI command and arguments
        parallel: Original parallel flag
        created_at: Original creation timestamp
        failed_at: Timestamp when moved to dead letter
        final_error: Error message from final retry attempt
        retry_count: Total number of attempts before failure
    """
    id: str
    job_type: str
    payload: dict
    parallel: bool
    created_at: float
    failed_at: float
    final_error: str
    retry_count: int


@dataclass
class QueueStats:
    """Queue health statistics.

    Provides metrics for monitoring queue status and capacity.
    Used by health check and status commands to detect backpressure.

    Attributes:
        pending: Number of jobs awaiting processing
        processing: Number of jobs currently being executed
        failed: Number of jobs that failed (not yet dead)
        dead_letter: Number of jobs in dead letter queue
        max_size: Maximum queue capacity (soft limit)
        capacity_pct: Percentage of max capacity used (0-100+)
    """
    pending: int
    processing: int
    failed: int
    dead_letter: int
    max_size: int
    capacity_pct: float = field(init=False)

    def __post_init__(self):
        """Calculate capacity percentage after initialization."""
        if self.max_size > 0:
            self.capacity_pct = (self.pending / self.max_size) * 100
        else:
            self.capacity_pct = 0.0
