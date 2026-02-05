"""Test suite for LLMRequestQueue.

Tests persistent queue operations, TTL handling, bounded queue behavior,
and ack/nack patterns.
"""

import time
from pathlib import Path

import pytest

from src.llm.config import LLMConfig
from src.llm.queue import LLMRequestQueue, QueuedRequest


@pytest.fixture
def test_config():
    """Test config with small queue limits."""
    return LLMConfig(
        queue_max_size=10,
        queue_item_ttl_hours=1,  # 1 hour for testing
    )


@pytest.fixture
def queue(test_config, tmp_path):
    """Create queue with temp storage path."""
    queue_path = tmp_path / "test_queue"
    return LLMRequestQueue(test_config, queue_path=queue_path)


class TestEnqueue:
    """Test request queueing."""

    def test_enqueue_returns_id(self, queue):
        """enqueue returns UUID for tracking."""
        request_id = queue.enqueue(
            operation="chat",
            params={"model": "test", "messages": []},
            error="Test error"
        )

        # Should be a UUID string
        assert isinstance(request_id, str)
        assert len(request_id) == 36  # UUID format
        assert "-" in request_id

    def test_enqueue_increments_count(self, queue):
        """Queue count increases after enqueue."""
        initial_count = queue.get_pending_count()

        queue.enqueue("chat", {}, "error1")
        assert queue.get_pending_count() == initial_count + 1

        queue.enqueue("generate", {}, "error2")
        assert queue.get_pending_count() == initial_count + 2

    def test_enqueue_stores_metadata(self, queue):
        """Queued items contain all required metadata."""
        params = {
            "model": "test-model",
            "messages": [{"role": "user", "content": "test"}]
        }
        error = "Cloud and local failed"

        request_id = queue.enqueue("chat", params, error)

        # Process the item to verify contents
        def check_item(operation, item_params):
            assert operation == "chat"
            assert item_params == params
            return True

        result = queue.process_one(check_item)
        assert result is True


class TestPendingCount:
    """Test pending count tracking."""

    def test_get_pending_count_empty(self, queue):
        """Empty queue returns 0."""
        assert queue.get_pending_count() == 0

    def test_get_pending_count_increases(self, queue):
        """Count increases with each enqueue."""
        assert queue.get_pending_count() == 0

        queue.enqueue("chat", {}, "error1")
        assert queue.get_pending_count() == 1

        queue.enqueue("chat", {}, "error2")
        assert queue.get_pending_count() == 2

        queue.enqueue("chat", {}, "error3")
        assert queue.get_pending_count() == 3


class TestProcessOne:
    """Test single item processing."""

    def test_process_one_success(self, queue):
        """Item acked on successful processing."""
        queue.enqueue("chat", {"test": "data"}, "error")

        # Processor succeeds
        def processor(operation, params):
            return {"success": True}

        result = queue.process_one(processor)

        assert result is True
        # Item should be removed
        assert queue.get_pending_count() == 0

    def test_process_one_failure(self, queue):
        """Item nacked on processing failure."""
        queue.enqueue("chat", {"test": "data"}, "error")

        # Processor fails
        def processor(operation, params):
            raise Exception("Processing failed")

        with pytest.raises(Exception, match="Processing failed"):
            queue.process_one(processor)

        # Item should still be in queue (nacked)
        assert queue.get_pending_count() == 1

    def test_process_one_empty_queue(self, queue):
        """Returns False when queue empty."""
        result = queue.process_one(lambda op, params: True)
        assert result is False


class TestStaleItems:
    """Test TTL-based expiry."""

    def test_stale_items_skipped(self, test_config, tmp_path):
        """Items older than TTL are skipped during processing."""
        queue_path = tmp_path / "stale_test_queue"
        queue = LLMRequestQueue(test_config, queue_path=queue_path)

        # Manually create a stale item by inserting with old timestamp
        import json
        from dataclasses import asdict
        from src.llm.queue import QueuedRequest
        import uuid

        stale_request = QueuedRequest(
            id=str(uuid.uuid4()),
            operation="chat",
            params={},
            timestamp=time.time() - (2 * 3600),  # 2 hours ago (TTL is 1 hour)
            original_error="test error"
        )
        queue._queue.put(asdict(stale_request))

        # Process - should skip stale item
        processed_count = 0

        def processor(operation, params):
            nonlocal processed_count
            processed_count += 1
            return True

        result = queue.process_one(processor)

        # Should return True (item was "processed" by skipping)
        assert result is True
        # Processor should NOT have been called (item was stale)
        assert processed_count == 0
        # Item should be removed (acked as stale)
        assert queue.get_pending_count() == 0

    def test_fresh_items_processed(self, queue):
        """Items within TTL are processed normally."""
        queue.enqueue("chat", {}, "error")

        processed = False

        def processor(operation, params):
            nonlocal processed
            processed = True
            return True

        result = queue.process_one(processor)

        assert result is True
        assert processed is True
        assert queue.get_pending_count() == 0


class TestBoundedQueue:
    """Test max_size enforcement."""

    def test_queue_bounded(self, test_config, tmp_path):
        """Queue respects max_size by removing oldest items."""
        # Config with very small max size
        config = LLMConfig(queue_max_size=3)
        queue_path = tmp_path / "bounded_queue"
        queue = LLMRequestQueue(config, queue_path=queue_path)

        # Fill queue to max
        queue.enqueue("chat", {"num": 1}, "error1")
        queue.enqueue("chat", {"num": 2}, "error2")
        queue.enqueue("chat", {"num": 3}, "error3")

        assert queue.get_pending_count() == 3

        # Add one more - should remove oldest
        queue.enqueue("chat", {"num": 4}, "error4")

        # Count should still be at max
        assert queue.get_pending_count() == 3

        # First item should be #2 (oldest was removed)
        def check_oldest(operation, params):
            # Should be item #2, not #1
            assert params["num"] == 2
            return True

        queue.process_one(check_oldest)


class TestQueueStats:
    """Test queue statistics."""

    def test_get_queue_stats_empty(self, queue):
        """Stats reflect empty queue state."""
        stats = queue.get_queue_stats()

        assert stats["pending"] == 0
        assert stats["max_size"] == 10  # From test_config
        assert stats["ttl_hours"] == 1   # From test_config

    def test_get_queue_stats_with_items(self, queue):
        """Stats reflect current queue state."""
        queue.enqueue("chat", {}, "error1")
        queue.enqueue("chat", {}, "error2")

        stats = queue.get_queue_stats()

        assert stats["pending"] == 2
        assert stats["max_size"] == 10
        assert stats["ttl_hours"] == 1


class TestPersistence:
    """Test queue persistence across reloads."""

    def test_persistence(self, test_config, tmp_path):
        """Queue survives reload from same path."""
        queue_path = tmp_path / "persistent_queue"

        # Create queue and add items
        queue1 = LLMRequestQueue(test_config, queue_path=queue_path)
        id1 = queue1.enqueue("chat", {"msg": "first"}, "error1")
        id2 = queue1.enqueue("generate", {"msg": "second"}, "error2")

        assert queue1.get_pending_count() == 2

        # Create new queue instance pointing to same path
        queue2 = LLMRequestQueue(test_config, queue_path=queue_path)

        # Should have same items
        assert queue2.get_pending_count() == 2

        # Process items to verify contents
        results = []

        def collector(operation, params):
            results.append((operation, params))
            return True

        queue2.process_one(collector)
        queue2.process_one(collector)

        assert len(results) == 2
        assert results[0] == ("chat", {"msg": "first"})
        assert results[1] == ("generate", {"msg": "second"})


class TestProcessAll:
    """Test batch processing."""

    def test_process_all_success(self, queue):
        """process_all processes all items when all succeed."""
        queue.enqueue("chat", {"num": 1}, "error1")
        queue.enqueue("chat", {"num": 2}, "error2")
        queue.enqueue("chat", {"num": 3}, "error3")

        def processor(operation, params):
            return True

        success, failure = queue.process_all(processor)

        assert success == 3
        assert failure == 0
        assert queue.get_pending_count() == 0

    def test_process_all_mixed_results(self, queue):
        """process_all tracks successes and failures."""
        queue.enqueue("chat", {"fail": False}, "error1")
        queue.enqueue("chat", {"fail": True}, "error2")
        queue.enqueue("chat", {"fail": False}, "error3")

        def processor(operation, params):
            if params["fail"]:
                raise Exception("Simulated failure")
            return True

        success, failure = queue.process_all(processor)

        assert success == 2
        assert failure == 1
        # Failed item should still be in queue
        assert queue.get_pending_count() == 1


class TestClearStale:
    """Test stale item cleanup."""

    def test_clear_stale_removes_old_items(self, queue):
        """clear_stale removes items older than TTL."""
        # Add items
        queue.enqueue("chat", {"num": 1}, "error1")
        queue.enqueue("chat", {"num": 2}, "error2")

        # Manually age one item
        item = queue._queue.get(block=False)
        item['timestamp'] = time.time() - (2 * 3600)  # 2 hours old (TTL is 1 hour)
        queue._queue.nack(item)

        # Clear stale
        removed = queue.clear_stale()

        assert removed == 1
        assert queue.get_pending_count() == 1  # One fresh item remains

    def test_clear_stale_keeps_fresh_items(self, queue):
        """clear_stale keeps items within TTL."""
        # Add recent items
        queue.enqueue("chat", {"num": 1}, "error1")
        queue.enqueue("chat", {"num": 2}, "error2")

        # Clear stale
        removed = queue.clear_stale()

        assert removed == 0
        assert queue.get_pending_count() == 2  # All items still present
