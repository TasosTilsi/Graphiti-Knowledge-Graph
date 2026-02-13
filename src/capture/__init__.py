"""Capture pipeline for automatic knowledge extraction.

This package provides the data processing pipeline that transforms raw git diffs
and conversation transcripts into clean, relevant knowledge graph entities via
LLM summarization.

Key components:
- git_capture: Extract commit data from git repositories
- git_worker: End-to-end git commit processing pipeline
- conversation: Claude Code transcript capture
- batching: Group items for batch processing (default: 10 items)
- relevance: Filter content for relevant knowledge
- summarizer: LLM-powered batch summarization

Usage:
    from src.capture import (
        read_and_clear_pending_commits,
        fetch_commit_diff,
        process_pending_commits,
        capture_conversation,
        BatchAccumulator,
        filter_relevant_commit,
        summarize_batch,
    )

    # Process pending git commits (high-level)
    entities = await process_pending_commits()

    # Capture conversation transcript
    entity = await capture_conversation(transcript_path, session_id)

    # Low-level: Read pending commits
    commits = read_and_clear_pending_commits()

    # Fetch diffs
    diffs = [fetch_commit_diff(sha) for sha in commits]

    # Filter for relevant content
    relevant = [d for d in diffs if filter_relevant_commit(d)]

    # Summarize batch
    summary = await summarize_batch(relevant)
"""

from src.capture.git_capture import (
    read_and_clear_pending_commits,
    fetch_commit_diff,
    append_pending_commit,
)
from src.capture.git_worker import (
    process_pending_commits,
    enqueue_git_processing,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_LINES_PER_FILE,
)
from src.capture.conversation import (
    capture_conversation,
    capture_manual,
    read_transcript,
    extract_conversation_text,
)
from src.capture.batching import BatchAccumulator
from src.capture.relevance import (
    filter_relevant_commit,
    get_active_categories,
    RELEVANCE_CATEGORIES,
    DEFAULT_CATEGORIES,
)
from src.capture.summarizer import (
    summarize_batch,
    summarize_and_store,
    BATCH_SUMMARIZATION_PROMPT,
)

__all__ = [
    # Git capture
    "read_and_clear_pending_commits",
    "fetch_commit_diff",
    "append_pending_commit",
    # Git worker
    "process_pending_commits",
    "enqueue_git_processing",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_MAX_LINES_PER_FILE",
    # Conversation capture
    "capture_conversation",
    "capture_manual",
    "read_transcript",
    "extract_conversation_text",
    # Batching
    "BatchAccumulator",
    # Relevance filtering
    "filter_relevant_commit",
    "get_active_categories",
    "RELEVANCE_CATEGORIES",
    "DEFAULT_CATEGORIES",
    # Summarization
    "summarize_batch",
    "summarize_and_store",
    "BATCH_SUMMARIZATION_PROMPT",
]