"""Test suite for OllamaClient with failover and retry logic.

Tests cloud-first/local-fallback pattern, retry behavior, cooldown management,
and error handling per CONTEXT.md decisions.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from ollama import ResponseError

from src.llm.client import LLMUnavailableError, OllamaClient
from src.llm.config import LLMConfig, get_state_path


@pytest.fixture
def mock_config(tmp_path):
    """LLM config with test values and temp paths."""
    return LLMConfig(
        cloud_endpoint="https://test-cloud.com",
        cloud_api_key="test_api_key",
        local_endpoint="http://localhost:11434",
        local_models=["test-model:3b", "test-model:1b"],
        embeddings_model="test-embed",
        retry_max_attempts=2,  # 1 initial + 1 retry
        retry_delay_seconds=1,  # Fast for tests
        quota_warning_threshold=0.8,
        rate_limit_cooldown_seconds=10,  # Short for tests
    )


@pytest.fixture(autouse=True)
def mock_state_path(tmp_path, monkeypatch):
    """Override state path to use temp directory (auto-applied to all tests)."""
    state_path = tmp_path / "llm_state.json"
    # Patch both imports - config module and client module
    monkeypatch.setattr("src.llm.config.get_state_path", lambda: state_path)
    monkeypatch.setattr("src.llm.client.get_state_path", lambda: state_path)
    return state_path


@pytest.fixture
def mock_queue_path(tmp_path):
    """Temp path for request queue."""
    return tmp_path / "llm_queue"


class TestCloudAvailability:
    """Test cloud availability checks."""

    def test_cloud_available_with_api_key(self, mock_config, mock_state_path, mock_queue_path):
        """Cloud available when API key set and not in cooldown."""
        client = OllamaClient(mock_config)
        assert client._is_cloud_available() is True

    def test_cloud_unavailable_without_api_key(self, mock_config, mock_state_path, mock_queue_path):
        """Cloud unavailable when no API key."""
        config_no_key = LLMConfig(
            cloud_api_key=None,  # No API key
        )
        client = OllamaClient(config_no_key)
        assert client._is_cloud_available() is False

    def test_cloud_unavailable_during_cooldown(self, mock_config, mock_state_path, mock_queue_path):
        """Cloud unavailable when in rate-limit cooldown."""
        client = OllamaClient(mock_config)

        # Set cooldown in the future
        client.cloud_cooldown_until = time.time() + 100
        assert client._is_cloud_available() is False

    def test_cloud_available_after_cooldown_expires(self, mock_config, mock_state_path, mock_queue_path):
        """Cloud becomes available after cooldown expires."""
        client = OllamaClient(mock_config)

        # Set cooldown in the past
        client.cloud_cooldown_until = time.time() - 1
        assert client._is_cloud_available() is True


class TestCooldownManagement:
    """Test cooldown state persistence and loading."""

    def test_rate_limit_triggers_cooldown(self, mock_config, mock_state_path, mock_queue_path):
        """429 error sets 10-minute cooldown."""
        client = OllamaClient(mock_config)

        # Simulate 429 error
        error = ResponseError(error="Rate limited", status_code=429)

        before_time = time.time()
        client._handle_cloud_error(error)
        after_time = time.time()

        # Cooldown should be set to approximately now + cooldown_seconds
        expected_cooldown = before_time + mock_config.rate_limit_cooldown_seconds
        assert client.cloud_cooldown_until >= expected_cooldown
        assert client.cloud_cooldown_until <= after_time + mock_config.rate_limit_cooldown_seconds + 1

    def test_non_rate_limit_error_no_cooldown(self, mock_config, mock_state_path, mock_queue_path):
        """Non-429 errors do NOT set cooldown."""
        client = OllamaClient(mock_config)

        # Record initial cooldown state (should be 0)
        initial_cooldown = client.cloud_cooldown_until

        # Simulate non-429 errors
        for status_code in [500, 502, 503, 504, 400, 401, 403]:
            error = ResponseError(error="Server error", status_code=status_code)
            client._handle_cloud_error(error)

            # Cooldown should NOT be modified
            assert client.cloud_cooldown_until == initial_cooldown

        # Cloud should still be available (assuming API key set)
        assert client._is_cloud_available() is True

    def test_cooldown_state_persisted(self, mock_config, mock_state_path, mock_queue_path):
        """Cooldown saved to llm_state.json."""
        client = OllamaClient(mock_config)

        # Set cooldown
        cooldown_time = time.time() + 600
        client.cloud_cooldown_until = cooldown_time
        client._save_cooldown_state()

        # Verify state file exists and contains cooldown
        assert mock_state_path.exists()
        state = json.loads(mock_state_path.read_text())
        assert "cloud_cooldown_until" in state
        assert state["cloud_cooldown_until"] == cooldown_time

    def test_cooldown_state_loaded(self, mock_config, mock_state_path, mock_queue_path):
        """Cooldown restored from file on init."""
        # Create state file with cooldown
        cooldown_time = time.time() + 600
        mock_state_path.write_text(json.dumps({"cloud_cooldown_until": cooldown_time}))

        # Create new client - should load cooldown
        client = OllamaClient(mock_config)
        assert client.cloud_cooldown_until == cooldown_time


class TestFailoverBehavior:
    """Test cloud-to-local failover."""

    def test_fallback_to_local(self, mock_config, mock_state_path, mock_queue_path):
        """Cloud failure falls back to local."""
        with patch("src.llm.client.Client") as MockClient:
            # Mock cloud to fail
            mock_cloud = Mock()
            mock_cloud.chat.side_effect = ResponseError(error="Cloud error", status_code=500)

            # Mock local to succeed
            mock_local = Mock()
            mock_local.list.return_value = {"models": [{"name": "test-model:3b"}]}
            mock_local.chat.return_value = {"message": {"content": "local response"}}

            # Return cloud first, then local
            MockClient.side_effect = [mock_cloud, mock_local]

            client = OllamaClient(mock_config)

            # Call should failover to local
            result = client.chat(messages=[{"role": "user", "content": "test"}])

            assert result == {"message": {"content": "local response"}}
            assert client.current_provider == "local"

    def test_cloud_retried_after_non_429_error(self, mock_config, mock_state_path, mock_queue_path):
        """After non-429 cloud error, cloud is tried on next request."""
        with patch("src.llm.client.Client") as MockClient:
            # Create single mock instances for cloud and local
            mock_cloud = Mock()
            mock_local = Mock()

            # Mock local list (for _check_local_models)
            mock_local.list.return_value = {"models": [{"name": "test-model:3b"}]}

            # First request: cloud fails BOTH retry attempts (500 errors)
            # Second request: cloud succeeds
            # Note: retry_max_attempts=2 means it will try twice per request
            mock_cloud.chat.side_effect = [
                ResponseError(error="Server error", status_code=500),  # First request, attempt 1
                ResponseError(error="Server error", status_code=500),  # First request, attempt 2 (retry)
                {"message": {"content": "cloud response 2"}},  # Second request, succeeds
            ]

            # Local always succeeds (fallback)
            mock_local.chat.return_value = {"message": {"content": "local response 1"}}

            # Return same instances (cloud, local) for OllamaClient init
            MockClient.side_effect = [mock_cloud, mock_local]

            client = OllamaClient(mock_config)

            # First request - cloud fails both retry attempts, fallback to local
            result1 = client.chat(messages=[{"role": "user", "content": "test1"}])
            assert result1 == {"message": {"content": "local response 1"}}

            # Verify cloud was NOT in cooldown after 500 error
            assert client._is_cloud_available() is True

            # Second request - cloud should be tried again (not skipped)
            # This time cloud succeeds
            result2 = client.chat(messages=[{"role": "user", "content": "test2"}])
            assert result2 == {"message": {"content": "cloud response 2"}}
            assert client.current_provider == "cloud"

            # Verify cloud.chat was called 3 times total (2 for first request, 1 for second)
            assert mock_cloud.chat.call_count == 3


class TestLocalModelFallback:
    """Test local model selection and fallback chain."""

    def test_local_model_fallback_chain(self, mock_config, mock_state_path, mock_queue_path):
        """Selects largest available model from fallback chain."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_local = Mock()

            # Both models available
            mock_local.list.return_value = {
                "models": [
                    {"name": "test-model:3b"},
                    {"name": "test-model:1b"},
                ]
            }

            # Mock successful response from the larger model
            mock_local.chat.return_value = {"message": {"content": "from largest model"}}

            MockClient.side_effect = [mock_cloud, mock_local]

            # Create client with no cloud key (skip cloud attempt)
            config_no_cloud = LLMConfig(
                cloud_api_key=None,
                local_models=["test-model:3b", "test-model:1b"],
            )
            client = OllamaClient(config_no_cloud)

            # Should select largest available model (3b > 1b)
            result = client.chat(messages=[{"role": "user", "content": "test"}])
            assert result == {"message": {"content": "from largest model"}}

            # Verify it called with the 3b model
            mock_local.chat.assert_called_once()
            call_args = mock_local.chat.call_args
            assert call_args[1]["model"] == "test-model:3b"

    def test_missing_model_error(self, mock_config, mock_state_path, mock_queue_path):
        """When model not available, request is queued and error includes request ID."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_local = Mock()

            # No models available
            mock_local.list.return_value = {"models": []}

            MockClient.side_effect = [mock_cloud, mock_local]

            # Create client with no cloud key
            config_no_cloud = LLMConfig(
                cloud_api_key=None,
                local_models=["missing-model:7b"],
            )
            client = OllamaClient(config_no_cloud)

            # Should raise LLMUnavailableError with queue ID
            with pytest.raises(LLMUnavailableError) as exc_info:
                client.chat(messages=[{"role": "user", "content": "test"}])

            error = exc_info.value
            # Should have request_id attribute
            assert error.request_id is not None
            # Error message should indicate queued
            error_msg = str(error)
            assert "queued for retry" in error_msg.lower()
            assert "id:" in error_msg.lower()


class TestProviderTracking:
    """Test current provider tracking."""

    def test_current_provider_tracking(self, mock_config, mock_state_path, mock_queue_path):
        """Current provider updates correctly."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_cloud.chat.return_value = {"message": {"content": "cloud response"}}

            mock_local = Mock()

            MockClient.side_effect = [mock_cloud, mock_local]

            client = OllamaClient(mock_config)

            # Initially no provider
            assert client.current_provider == "none"

            # After cloud success
            result = client.chat(messages=[{"role": "user", "content": "test"}])
            assert client.current_provider == "cloud"


class TestTotalFailure:
    """Test behavior when both cloud and local fail."""

    def test_both_fail_raises_unavailable(self, mock_config, mock_state_path, mock_queue_path):
        """LLMUnavailableError when both cloud and local fail."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()
            mock_cloud.chat.side_effect = ResponseError(error="Cloud error", status_code=500)

            mock_local = Mock()
            mock_local.list.side_effect = Exception("Local not running")

            MockClient.side_effect = [mock_cloud, mock_local]

            client = OllamaClient(mock_config)

            # Both should fail - raises LLMUnavailableError
            with pytest.raises(LLMUnavailableError):
                client.chat(messages=[{"role": "user", "content": "test"}])


class TestLLMUnavailableError:
    """Test LLMUnavailableError message format per CONTEXT.md."""

    def test_llm_unavailable_error_message_no_id(self):
        """LLMUnavailableError() produces default message."""
        error = LLMUnavailableError()
        assert str(error) == "LLM unavailable. Request will be queued for retry."

    def test_llm_unavailable_error_message_with_id(self):
        """LLMUnavailableError(request_id=...) includes ID in message."""
        error = LLMUnavailableError(request_id="abc-123-def-456")
        expected = "LLM unavailable. Request queued for retry. ID: abc-123-def-456"
        assert str(error) == expected

    def test_llm_unavailable_error_custom_message(self):
        """LLMUnavailableError with custom message preserves it."""
        custom_msg = "Custom error: connection timeout"
        error = LLMUnavailableError(custom_msg)
        assert str(error) == custom_msg

    def test_llm_unavailable_error_id_attribute(self):
        """LLMUnavailableError stores request_id as attribute."""
        error = LLMUnavailableError(request_id="test-id-123")
        assert error.request_id == "test-id-123"


class TestRetryLogic:
    """Test retry behavior with tenacity."""

    def test_retry_on_cloud_error(self, mock_config, mock_state_path, mock_queue_path):
        """Verify tenacity retry happens before failover."""
        with patch("src.llm.client.Client") as MockClient:
            mock_cloud = Mock()

            # Fail twice, succeed on third attempt
            mock_cloud.chat.side_effect = [
                ResponseError(error="Temporary error", status_code=503),
                ResponseError(error="Temporary error", status_code=503),
                {"message": {"content": "success after retry"}},
            ]

            mock_local = Mock()

            MockClient.side_effect = [mock_cloud, mock_local]

            # Config with retry_max_attempts=3 (1 initial + 2 retries)
            config_with_retry = LLMConfig(
                cloud_api_key="test_key",
                retry_max_attempts=3,
                retry_delay_seconds=0.1,  # Fast retry for test
            )
            client = OllamaClient(config_with_retry)

            # Should retry and eventually succeed
            result = client.chat(messages=[{"role": "user", "content": "test"}])
            assert result == {"message": {"content": "success after retry"}}
            assert client.current_provider == "cloud"

            # Verify cloud.chat was called 3 times (2 failures + 1 success)
            assert mock_cloud.chat.call_count == 3
