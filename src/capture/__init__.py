"""Capture pipeline for automatic knowledge extraction.

This package provides the data processing pipeline that transforms raw git diffs
and conversation transcripts into clean, relevant knowledge graph entities via
LLM summarization.

Key components:
- git_capture: Extract commit data from git repositories
- batching: Group items for batch processing (default: 10 items)
- relevance: Filter content for relevant knowledge
- summarizer: LLM-powered batch summarization

Usage:
    from src.capture import (
        read_and_clear_pending_commits,
        fetch_commit_diff,
        BatchAccumulator,
        filter_relevant_commit,
        summarize_batch,
    )
    
    # Read pending commits
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