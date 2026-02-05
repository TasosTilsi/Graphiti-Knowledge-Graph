"""LLM integration module.

This module provides LLM configuration and client management for the
graphiti-knowledge-graph system. It supports both cloud and local Ollama
endpoints with automatic failover and retry logic.
"""

from .config import LLMConfig, load_config

__all__ = ["LLMConfig", "load_config"]
