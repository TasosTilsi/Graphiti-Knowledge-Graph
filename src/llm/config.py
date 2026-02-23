"""LLM configuration management.

This module provides configuration management for LLM operations including:
- TOML-based configuration with sensible defaults
- Environment variable overrides for sensitive data
- Type-safe configuration via frozen dataclass
"""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LLMConfig:
    """LLM configuration.

    Frozen dataclass ensures immutable configuration after load.
    All fields have sensible defaults for immediate use.
    """

    # Cloud endpoint configuration
    cloud_endpoint: str = "https://ollama.com"
    cloud_api_key: str | None = None

    # Local endpoint configuration
    local_endpoint: str = "http://localhost:11434"
    local_auto_start: bool = False
    local_models: list[str] = field(default_factory=lambda: ["gemma2:9b", "llama3.2:3b"])

    # Embeddings model
    embeddings_model: str = "nomic-embed-text"

    # Retry configuration
    retry_max_attempts: int = 3  # 1 initial + 2 retries
    retry_delay_seconds: int = 10  # Fixed delay

    # Timeout configuration (local models need more time for structured output prompts)
    request_timeout_seconds: int = 180

    # Quota management
    quota_warning_threshold: float = 0.8  # Warn at 80%
    rate_limit_cooldown_seconds: int = 600  # 10 minutes

    # Logging
    failover_logging: bool = True  # Log every failover

    # Queue management
    queue_max_size: int = 1000  # Bounded queue
    queue_item_ttl_hours: int = 24  # Skip stale items

    # Reranking configuration
    reranking_enabled: bool = False
    reranking_backend: str = "none"  # "none", "bge", "openai"


def load_config(config_path: Path | None = None) -> LLMConfig:
    """Load LLM configuration from TOML file with environment overrides.

    Priority: environment variables > TOML file > defaults

    Args:
        config_path: Path to TOML config file.
                    Defaults to ~/.graphiti/llm.toml

    Returns:
        Frozen LLMConfig instance
    """
    if config_path is None:
        config_path = Path.home() / ".graphiti" / "llm.toml"

    # Load TOML config if exists
    config_data = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)

    # Extract values from TOML structure
    cloud = config_data.get("cloud", {})
    local = config_data.get("local", {})
    embeddings = config_data.get("embeddings", {})
    retry = config_data.get("retry", {})
    timeout = config_data.get("timeout", {})
    quota = config_data.get("quota", {})
    logging = config_data.get("logging", {})
    queue = config_data.get("queue", {})
    reranking = config_data.get("reranking", {})

    # Apply environment variable overrides
    cloud_endpoint = os.getenv("OLLAMA_CLOUD_ENDPOINT", cloud.get("endpoint", "https://ollama.com"))
    cloud_api_key = os.getenv("OLLAMA_API_KEY", cloud.get("api_key"))
    local_endpoint = os.getenv("OLLAMA_LOCAL_ENDPOINT", local.get("endpoint", "http://localhost:11434"))

    return LLMConfig(
        cloud_endpoint=cloud_endpoint,
        cloud_api_key=cloud_api_key,
        local_endpoint=local_endpoint,
        local_auto_start=local.get("auto_start", False),
        local_models=local.get("models", ["gemma2:9b", "llama3.2:3b"]),
        embeddings_model=embeddings.get("model", "nomic-embed-text"),
        retry_max_attempts=retry.get("max_attempts", 3),
        retry_delay_seconds=retry.get("delay_seconds", 10),
        request_timeout_seconds=timeout.get("request_seconds", 90),
        quota_warning_threshold=quota.get("warning_threshold", 0.8),
        rate_limit_cooldown_seconds=quota.get("rate_limit_cooldown_seconds", 600),
        failover_logging=logging.get("failover", True),
        queue_max_size=queue.get("max_size", 1000),
        queue_item_ttl_hours=queue.get("item_ttl_hours", 24),
        reranking_enabled=reranking.get("enabled", False),
        reranking_backend=reranking.get("backend", "none"),
    )


def get_state_path() -> Path:
    """Get path for LLM state persistence.

    Returns path to llm_state.json for cooldown tracking.
    """
    return Path.home() / ".graphiti" / "llm_state.json"
