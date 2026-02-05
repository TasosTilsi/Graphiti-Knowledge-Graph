"""OllamaClient with cloud-first failover and retry logic.

This module provides the core LLM client that implements the cloud-first/local-fallback
pattern. All LLM operations flow through this client which handles retries, cooldowns,
and automatic failover per the decisions in CONTEXT.md.
"""

import json
import re
import time
from pathlib import Path

import httpx
import structlog
from ollama import Client, ResponseError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from src.llm.config import LLMConfig, get_state_path

logger = structlog.get_logger()


class LLMUnavailableError(Exception):
    """Raised when both cloud and local LLM providers fail.

    Message format per CONTEXT.md:
      "LLM unavailable. Request queued for retry. ID: <uuid>"

    The request_id is populated by the queue module (Plan 03-04).
    Before queue integration, request_id is None and message is:
      "LLM unavailable. Request will be queued for retry."
    """

    def __init__(self, message: str | None = None, request_id: str | None = None):
        self.request_id = request_id
        if message is None:
            if request_id:
                message = f"LLM unavailable. Request queued for retry. ID: {request_id}"
            else:
                message = "LLM unavailable. Request will be queued for retry."
        super().__init__(message)


class OllamaClient:
    """Ollama client with cloud-first failover and automatic retry.

    Implements the cloud-first/local-fallback pattern with:
    - Cloud Ollama tried first when not in cooldown
    - Automatic retry with fixed delay on errors
    - Rate-limit (429) triggers 10-minute cooldown
    - Non-rate-limit errors do NOT set cooldown; cloud is tried on next request
    - Automatic failover to local Ollama on cloud failure
    - Clear error messages for missing local models
    """

    def __init__(self, config: LLMConfig):
        """Initialize OllamaClient with configuration.

        Args:
            config: LLM configuration (from load_config())
        """
        self.config = config
        self._current_provider: str = "none"

        # Configure cloud client with authentication and timeouts
        cloud_headers = {}
        if config.cloud_api_key:
            cloud_headers["Authorization"] = f"Bearer {config.cloud_api_key}"

        cloud_timeout = httpx.Timeout(
            connect=5.0,
            read=config.request_timeout_seconds,
            write=10.0,
            pool=20.0,
        )

        self.cloud_client = Client(
            host=config.cloud_endpoint,
            headers=cloud_headers,
            timeout=cloud_timeout,
        )

        # Configure local client with shorter timeouts
        local_timeout = httpx.Timeout(
            connect=2.0,
            read=60.0,
            write=10.0,
            pool=5.0,
        )

        self.local_client = Client(
            host=config.local_endpoint,
            timeout=local_timeout,
        )

        # Initialize cooldown state
        self.cloud_cooldown_until = 0  # Unix timestamp
        self._load_cooldown_state()

        # Handle local_auto_start config
        # TODO: local_auto_start implementation deferred. Config field exists for future use.
        if config.local_auto_start:
            logger.debug(
                "local_auto_start is configured but auto-start is not yet implemented. "
                "Start Ollama manually: ollama serve"
            )

        logger.debug(
            "OllamaClient initialized",
            cloud_endpoint=config.cloud_endpoint,
            local_endpoint=config.local_endpoint,
            has_api_key=bool(config.cloud_api_key),
        )

    def _is_cloud_available(self) -> bool:
        """Check if cloud Ollama can be used.

        IMPORTANT: This method ONLY checks rate-limit cooldown. Non-429 errors do NOT
        set any cooldown, so cloud is always tried again on the very next request after
        a non-rate-limit failure. This is by design per CONTEXT.md.

        Returns:
            True if cloud API key is set and not in rate-limit cooldown
        """
        if not self.config.cloud_api_key:
            return False

        current_time = time.time()
        is_available = current_time >= self.cloud_cooldown_until

        if not is_available:
            remaining = int(self.cloud_cooldown_until - current_time)
            logger.debug(
                "Cloud in rate-limit cooldown",
                remaining_seconds=remaining,
            )

        return is_available

    def _load_cooldown_state(self):
        """Load cooldown state from disk if exists."""
        state_path = get_state_path()
        if not state_path.exists():
            return

        try:
            with open(state_path) as f:
                state = json.load(f)
                self.cloud_cooldown_until = state.get("cloud_cooldown_until", 0)
                logger.debug(
                    "Cooldown state loaded",
                    cloud_cooldown_until=self.cloud_cooldown_until,
                )
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "Failed to load cooldown state, starting fresh",
                error=str(e),
            )

    def _save_cooldown_state(self):
        """Save cooldown state to disk for persistence across restarts."""
        state_path = get_state_path()

        # Ensure parent directory exists
        state_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(state_path, "w") as f:
                json.dump({"cloud_cooldown_until": self.cloud_cooldown_until}, f)
        except OSError as e:
            logger.warning(
                "Failed to save cooldown state",
                error=str(e),
            )

    def _handle_cloud_error(self, error: ResponseError):
        """Handle cloud error with appropriate cooldown and logging.

        Args:
            error: ResponseError from cloud Ollama
        """
        if error.status_code == 429:
            # Rate limit: Set 10-minute cooldown
            self.cloud_cooldown_until = time.time() + self.config.rate_limit_cooldown_seconds
            self._save_cooldown_state()
            logger.warning(
                "Cloud rate-limited (429). Cooldown activated",
                cooldown_seconds=self.config.rate_limit_cooldown_seconds,
                cooldown_until=self.cloud_cooldown_until,
            )
        else:
            # CONTEXT.md decision: Non-rate-limit errors do NOT set cooldown.
            # Cloud will be tried again on the very next request.
            # Only 429 errors trigger the 10-minute cooldown period.
            logger.warning(
                "Cloud error (non-rate-limit)",
                status_code=error.status_code,
                error=str(error.error),
            )

        # Log failover event if configured
        if self.config.failover_logging:
            logger.info(
                "llm_failover",
                from_provider="cloud",
                to_provider="local",
                reason="rate_limit" if error.status_code == 429 else "error",
                error_code=error.status_code,
            )

    def _retry_cloud(self, operation: str, **kwargs):
        """Retry cloud operation with tenacity.

        Args:
            operation: Operation name ("chat", "generate", or "embed")
            **kwargs: Arguments to pass to the operation

        Returns:
            Operation result

        Raises:
            ResponseError: If all retry attempts fail
        """

        @retry(
            stop=stop_after_attempt(self.config.retry_max_attempts),
            wait=wait_fixed(self.config.retry_delay_seconds),
            retry=retry_if_exception_type((ConnectionError, ResponseError)),
            before_sleep=lambda retry_state: logger.info(
                "Retrying cloud request",
                attempt=retry_state.attempt_number,
                max_attempts=self.config.retry_max_attempts,
                delay_seconds=self.config.retry_delay_seconds,
            ),
        )
        def _do_retry():
            if operation == "chat":
                return self.cloud_client.chat(**kwargs)
            elif operation == "generate":
                return self.cloud_client.generate(**kwargs)
            elif operation == "embed":
                return self.cloud_client.embed(**kwargs)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        result = _do_retry()
        self._current_provider = "cloud"
        return result

    def _check_local_models(self) -> list[str]:
        """Check which models are available in local Ollama.

        Returns:
            List of available model names

        Raises:
            LLMUnavailableError: If local Ollama is not running
        """
        try:
            response = self.local_client.list()
            return [model["name"] for model in response.get("models", [])]
        except Exception as e:
            raise LLMUnavailableError(
                "Local Ollama not running. Start with: ollama serve"
            ) from e

    def _try_local(self, operation: str, model: str | None, **kwargs):
        """Try operation with local Ollama.

        Args:
            operation: Operation name ("chat", "generate", or "embed")
            model: Model name (None = use fallback chain)
            **kwargs: Arguments to pass to the operation

        Returns:
            Operation result

        Raises:
            LLMUnavailableError: If local Ollama unavailable or models not pulled
        """
        # Check local Ollama is running
        available_models = self._check_local_models()

        # Determine which model to use
        if model is not None:
            # Specific model requested
            if model not in available_models:
                raise LLMUnavailableError(
                    f"Model {model} not available. Run: ollama pull {model}"
                )
            models_to_try = [model]
        else:
            # Use fallback chain
            models_to_try = [
                m for m in self.config.local_models if m in available_models
            ]
            if not models_to_try:
                missing = ", ".join(self.config.local_models)
                raise LLMUnavailableError(
                    f"No configured models available. Run: ollama pull {missing}"
                )

            # Select largest available model
            models_to_try = [get_largest_available_model(models_to_try, available_models)]

        # Try each model in order
        last_error = None
        for model_name in models_to_try:
            try:
                kwargs["model"] = model_name
                if operation == "chat":
                    result = self.local_client.chat(**kwargs)
                elif operation == "generate":
                    result = self.local_client.generate(**kwargs)
                elif operation == "embed":
                    result = self.local_client.embed(**kwargs)
                else:
                    raise ValueError(f"Unknown operation: {operation}")

                self._current_provider = "local"
                logger.debug(
                    "Local operation succeeded",
                    operation=operation,
                    model=model_name,
                )
                return result
            except Exception as e:
                last_error = e
                logger.debug(
                    "Local model failed, trying next",
                    model=model_name,
                    error=str(e),
                )

        # All models failed
        raise LLMUnavailableError(
            f"All local models failed. Last error: {last_error}"
        ) from last_error

    def chat(self, model: str | None = None, messages: list[dict] | None = None, **kwargs):
        """Send chat completion request with automatic failover.

        Args:
            model: Model name (None = use cloud default or local fallback)
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional arguments for ollama.chat()

        Returns:
            Chat completion response

        Raises:
            LLMUnavailableError: If both cloud and local fail
        """
        # Try cloud if available
        if self._is_cloud_available():
            try:
                cloud_model = model or self.config.local_models[0]  # Default to first configured
                return self._retry_cloud("chat", model=cloud_model, messages=messages, **kwargs)
            except ResponseError as e:
                self._handle_cloud_error(e)
                # Fall through to local

        # Fallback to local
        return self._try_local("chat", model, messages=messages, **kwargs)

    def generate(self, model: str | None = None, prompt: str | None = None, **kwargs):
        """Send generate request with automatic failover.

        Args:
            model: Model name (None = use cloud default or local fallback)
            prompt: Prompt text
            **kwargs: Additional arguments for ollama.generate()

        Returns:
            Generate response

        Raises:
            LLMUnavailableError: If both cloud and local fail
        """
        # Try cloud if available
        if self._is_cloud_available():
            try:
                cloud_model = model or self.config.local_models[0]  # Default to first configured
                return self._retry_cloud("generate", model=cloud_model, prompt=prompt, **kwargs)
            except ResponseError as e:
                self._handle_cloud_error(e)
                # Fall through to local

        # Fallback to local
        return self._try_local("generate", model, prompt=prompt, **kwargs)

    def embed(self, model: str | None = None, input: str | list[str] | None = None, **kwargs):
        """Send embeddings request with automatic failover.

        Args:
            model: Model name (None = use embeddings_model from config)
            input: Text or list of texts to embed
            **kwargs: Additional arguments for ollama.embed()

        Returns:
            Embeddings response

        Raises:
            LLMUnavailableError: If both cloud and local fail
        """
        # Default to embeddings model
        embed_model = model or self.config.embeddings_model

        # Try cloud if available
        if self._is_cloud_available():
            try:
                return self._retry_cloud("embed", model=embed_model, input=input, **kwargs)
            except ResponseError as e:
                self._handle_cloud_error(e)
                # Fall through to local

        # Fallback to local
        return self._try_local("embed", embed_model, input=input, **kwargs)

    @property
    def current_provider(self) -> str:
        """Get the current active provider.

        Returns:
            "cloud", "local", or "none"
        """
        return self._current_provider


def get_largest_available_model(models: list[str], available: list[str]) -> str | None:
    """Select largest model from list based on parameter count.

    Args:
        models: List of model names to consider
        available: List of available model names

    Returns:
        Largest available model name, or None if none available
    """
    # Filter to only available models
    available_set = set(available)
    candidates = [m for m in models if m in available_set]

    if not candidates:
        return None

    def extract_params(model_name: str) -> int:
        """Extract parameter count from model name.

        Examples:
            "gemma2:9b" -> 9_000_000_000
            "llama3.2:3B" -> 3_000_000_000
            "nomic-embed-text" -> 0
        """
        match = re.search(r"(\d+)b", model_name.lower())
        if match:
            return int(match.group(1)) * 1_000_000_000
        return 0

    # Sort by parameter count descending, return largest
    return max(candidates, key=extract_params)
