"""End-to-end integration tests for LLM module.

Tests complete LLM flow with mocked Ollama services, including:
- Cloud success flow
- Cloud-to-local failover
- Rate-limit cooldown behavior
- Non-429 error retry behavior
- Request queueing on total failure
- Singleton client behavior
- Queue processing
"""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from ollama import ResponseError

from src.llm import (
    chat,
    embed,
    generate,
    get_client,
    get_status,
    reset_client,
)
from src.llm.client import LLMUnavailableError
from src.llm.config import LLMConfig


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton client before each test."""
    reset_client()
    yield
    reset_client()


@pytest.fixture(autouse=True)
def mock_state_path(tmp_path, monkeypatch):
    """Override state path for all tests."""
    import time
    # Unique paths per test to avoid pollution
    unique_id = time.time_ns()
    state_path = tmp_path / f"llm_state_{unique_id}.json"
    queue_path = tmp_path / f"llm_queue_{unique_id}"

    monkeypatch.setattr("src.llm.config.get_state_path", lambda: state_path)
    monkeypatch.setattr("src.llm.client.get_state_path", lambda: state_path)

    # Patch LLMRequestQueue init to use unique queue path
    original_init = __import__("src.llm.queue", fromlist=["LLMRequestQueue"]).LLMRequestQueue.__init__

    def patched_init(self, config, queue_path_arg=None):
        # Always use our unique queue path
        original_init(self, config, queue_path=queue_path)

    monkeypatch.setattr("src.llm.queue.LLMRequestQueue.__init__", patched_init)

    return state_path


@pytest.fixture
def test_config(tmp_path):
    """Test configuration with temp paths."""
    import time
    # Use unique queue path per test to avoid cross-test pollution
    unique_queue = tmp_path / f"queue_{time.time_ns()}"
    return LLMConfig(
        cloud_endpoint="https://test-cloud.com",
        cloud_api_key="test_key",
        cloud_models=["test-cloud-model"],
        local_endpoint="http://localhost:11434",
        local_models=["test-model:3b"],
        embeddings_models=["test-embed"],
        retry_max_attempts=2,
        retry_delay_seconds=0.1,
        rate_limit_cooldown_seconds=10,
    )


class TestChatIntegration:
    """Integration tests for chat flow."""

    def test_chat_cloud_success(self, test_config):
        """Cloud chat succeeds - quota tracked."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_cloud.chat.return_value = {
                "message": {"content": "cloud chat response"}
            }
            mock_local = Mock()

            MockClient.side_effect = [mock_cloud, mock_local]

            # Initialize client with test config
            client = get_client(test_config)

            # Call chat
            response = client.chat(messages=[{"role": "user", "content": "test"}])

            assert response == {"message": {"content": "cloud chat response"}}

            # Verify cloud was used
            status = get_status()
            assert status["current_provider"] == "cloud"

    def test_chat_cloud_fail_local_success(self, test_config):
        """Cloud fails, fallback to local succeeds."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_cloud.chat.side_effect = [
                ResponseError(error="Cloud error", status_code=500),
                ResponseError(error="Cloud error", status_code=500),  # Both retries fail
            ]

            mock_local = Mock()
            mock_local.list.return_value = {"models": [{"name": "test-model:3b"}]}
            mock_local.chat.return_value = {
                "message": {"content": "local chat response"}
            }

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)
            response = client.chat(messages=[{"role": "user", "content": "test"}])

            assert response == {"message": {"content": "local chat response"}}

            status = get_status()
            assert status["current_provider"] == "local"


class TestRateLimitBehavior:
    """Integration tests for rate-limit cooldown."""

    def test_chat_rate_limit_cooldown(self, test_config):
        """429 error triggers cooldown, subsequent requests use local."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_local = Mock()

            # First request: 429 rate limit (4xx errors are NOT retried — only 5xx/ConnectionError)
            mock_cloud.chat.side_effect = [
                ResponseError(error="Rate limited", status_code=429),
                # Second request would NOT reach cloud (cooldown active)
            ]

            mock_local.list.return_value = {"models": [{"name": "test-model:3b"}]}
            mock_local.chat.return_value = {
                "message": {"content": "local response"}
            }

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)

            # First request - hits rate limit, falls back to local
            result1 = chat([{"role": "user", "content": "test1"}])
            assert result1 == {"message": {"content": "local response"}}

            # Verify cooldown is active
            assert client._is_cloud_available() is False

            # Second request - cloud should be skipped (in cooldown)
            result2 = chat([{"role": "user", "content": "test2"}])
            assert result2 == {"message": {"content": "local response"}}

            # Cloud called exactly once (first request only — 429 not retried, second skipped)
            assert mock_cloud.chat.call_count == 1

    def test_chat_non_429_error_cloud_retried(self, test_config):
        """Non-429 errors do NOT set cooldown; cloud retried on next request."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_local = Mock()

            # First request: 500 error (both retries)
            # Second request: cloud succeeds
            mock_cloud.chat.side_effect = [
                ResponseError(error="Server error", status_code=500),
                ResponseError(error="Server error", status_code=500),
                {"message": {"content": "cloud success on retry"}},
            ]

            mock_local.list.return_value = {"models": [{"name": "test-model:3b"}]}
            mock_local.chat.return_value = {
                "message": {"content": "local fallback"}
            }

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)

            # First request - 500 errors, falls back to local
            result1 = chat([{"role": "user", "content": "test1"}])
            assert result1 == {"message": {"content": "local fallback"}}

            # Verify NO cooldown after 500 error
            assert client._is_cloud_available() is True

            # Second request - cloud should be tried again
            result2 = chat([{"role": "user", "content": "test2"}])
            assert result2 == {"message": {"content": "cloud success on retry"}}

            # Verify cloud.chat was called 3 times (2 for first request, 1 for second)
            assert mock_cloud.chat.call_count == 3


class TestTotalFailure:
    """Integration tests for queue-and-raise pattern."""

    def test_chat_both_fail_queued(self, test_config):
        """Both cloud and local fail - request queued with ID."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_cloud.chat.side_effect = [
                ResponseError(error="Cloud error", status_code=503),
                ResponseError(error="Cloud error", status_code=503),
            ]

            mock_local = Mock()
            mock_local.list.side_effect = Exception("Local not running")

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)

            # Should raise LLMUnavailableError with request ID
            with pytest.raises(LLMUnavailableError) as exc_info:
                client.chat(messages=[{"role": "user", "content": "test"}])

            error = exc_info.value
            # Should have request_id
            assert error.request_id is not None
            # Error message should match format
            error_msg = str(error)
            assert "queued for retry" in error_msg.lower()
            assert "id:" in error_msg.lower()
            assert error.request_id in error_msg

            # Verify request is in queue
            status = get_status()
            assert status["queue"]["pending"] == 1


class TestEmbeddings:
    """Integration tests for embeddings."""

    def test_embed_uses_nomic(self, test_config):
        """Embed uses configured embeddings model (always local — cloud embed disabled)."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_local = Mock()
            # Embed is local-only (_is_cloud_available("embed") hard-returns False)
            mock_local.list.return_value = {"models": [{"name": "test-embed:latest"}]}
            mock_local.embed.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)
            response = client.embed(input="test text")

            assert response == {"embeddings": [[0.1, 0.2, 0.3]]}

            # Verify embed was called locally with the configured model
            mock_local.embed.assert_called_once()
            call_args = mock_local.embed.call_args
            assert call_args[1]["model"] in ("test-embed", "test-embed:latest")


class TestStatusAndMonitoring:
    """Integration tests for status and monitoring."""

    def test_get_status_complete(self, test_config):
        """get_status returns provider, quota, queue info."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_cloud.chat.return_value = {"message": {"content": "test"}}
            mock_local = Mock()

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)

            # Make a request to set provider
            client.chat(messages=[{"role": "user", "content": "test"}])

            status = get_status()

            # Should have all required fields
            assert "current_provider" in status
            assert "quota" in status
            assert "queue" in status

            assert status["current_provider"] == "cloud"
            assert status["quota"] is not None
            assert "pending" in status["queue"]


class TestSingletonClient:
    """Integration tests for singleton pattern."""

    def test_singleton_client(self, test_config):
        """get_client returns same instance."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_local = Mock()
            MockClient.side_effect = [mock_cloud, mock_local]

            client1 = get_client(test_config)
            client2 = get_client(test_config)

            # Same instance
            assert client1 is client2

    def test_reset_client_creates_new_instance(self, test_config):
        """reset_client clears singleton."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud1 = Mock()
            mock_local1 = Mock()
            mock_cloud2 = Mock()
            mock_local2 = Mock()
            MockClient.side_effect = [
                mock_cloud1,
                mock_local1,
                mock_cloud2,
                mock_local2,
            ]

            client1 = get_client(test_config)
            reset_client()
            client2 = get_client(test_config)

            # Different instances
            assert client1 is not client2


class TestQueueProcessing:
    """Integration tests for queue retry processing."""

    def test_queue_retry_processing(self, test_config):
        """Queue processes failed requests on retry."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_local = Mock()

            # First request: both fail (will be queued)
            mock_cloud.chat.side_effect = [
                ResponseError(error="Temporary error", status_code=503),
                ResponseError(error="Temporary error", status_code=503),
                # Queue processing: cloud succeeds
                {"message": {"content": "retried successfully"}},
            ]

            mock_local.list.side_effect = [
                Exception("Local not running"),  # First request
                {"models": [{"name": "test-model:3b"}]},  # Queue processing
            ]

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)

            # First request - both fail, queued
            with pytest.raises(LLMUnavailableError):
                chat([{"role": "user", "content": "test"}])

            # Verify queued
            assert client.get_queue_stats()["pending"] == 1

            # Now process queue (cloud succeeds this time)
            success, failure = client.process_queue()

            assert success == 1
            assert failure == 0
            assert client.get_queue_stats()["pending"] == 0


class TestGenerateAPI:
    """Integration tests for generate API."""

    def test_generate_flow(self, test_config):
        """Generate API works end-to-end."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_cloud.generate.return_value = {
                "response": "Generated text from prompt"
            }
            mock_local = Mock()

            MockClient.side_effect = [mock_cloud, mock_local]

            client = get_client(test_config)
            response = client.generate(prompt="Test prompt")

            assert response == {"response": "Generated text from prompt"}
            mock_cloud.generate.assert_called_once()
