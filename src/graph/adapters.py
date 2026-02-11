"""Adapters that bridge our Ollama client to graphiti_core interfaces.

OllamaLLMClient adapts our src.llm.chat() to graphiti_core's LLMClient ABC.
OllamaEmbedder adapts our src.llm.embed() to graphiti_core's EmbedderClient ABC.

Both adapters handle the async/sync bridge since graphiti_core is async
but our OllamaClient is synchronous.
"""

import asyncio
import json
import logging
from typing import Any, Iterable

from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import LLMConfig as GraphitiLLMConfig, ModelSize
from graphiti_core.prompts.models import Message
from pydantic import BaseModel

from src.llm import chat as ollama_chat, embed as ollama_embed

logger = logging.getLogger(__name__)


class OllamaLLMClient(LLMClient):
    """Adapter that routes graphiti_core LLM calls through our OllamaClient.

    This adapter implements graphiti_core's abstract LLMClient interface,
    routing all requests through our src.llm module which handles:
    - Cloud/local failover
    - Rate limiting and cooldowns
    - Request queuing on failures
    - Quota tracking

    The adapter bridges the async/sync gap: graphiti_core is async,
    our OllamaClient is sync (makes blocking HTTP calls).
    """

    def __init__(self):
        """Initialize OllamaLLMClient.

        Creates a minimal GraphitiLLMConfig with model=None since we route
        through our own client which manages model selection.
        """
        # Create minimal config - we don't use graphiti's model selection
        config = GraphitiLLMConfig(model=None)
        super().__init__(config)
        logger.debug("OllamaLLMClient initialized")

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = 8192,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        """Generate response from messages via our Ollama client.

        Args:
            messages: List of Message objects with role and content
            response_model: Optional Pydantic model for structured output
            max_tokens: Maximum tokens in response (unused - our client manages)
            model_size: Model size hint (unused - our client manages)

        Returns:
            Dict with response content or parsed model dict

        Raises:
            Exception: If LLM call fails (propagates from our client)
        """
        # Convert Message objects to dicts for our client
        message_dicts = [{"role": m.role, "content": m.content} for m in messages]

        logger.debug(
            "Generating response",
            num_messages=len(message_dicts),
            has_response_model=response_model is not None,
        )

        try:
            # Call our sync ollama_chat in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama_chat(messages=message_dicts),
            )

            # Extract response content
            response_text = response["message"]["content"]

            # If response_model provided, parse as JSON and validate
            if response_model is not None:
                try:
                    # Try to parse the response as JSON
                    parsed_data = json.loads(response_text)
                    # Validate against the model
                    validated = response_model.model_validate(parsed_data)
                    # Return as dict
                    return validated.model_dump()
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        "Failed to parse response as structured output",
                        error=str(e),
                        response_preview=response_text[:200],
                    )
                    # Fall back to returning content as-is
                    return {"content": response_text}

            # No response model - return plain content
            return {"content": response_text}

        except Exception as e:
            logger.error(
                "Failed to generate response",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class OllamaEmbedder(EmbedderClient):
    """Adapter that routes graphiti_core embedding calls through our Ollama client.

    This adapter implements graphiti_core's abstract EmbedderClient interface,
    routing all embedding requests through our src.llm.embed() function which
    handles cloud/local failover automatically.
    """

    def __init__(self):
        """Initialize OllamaEmbedder."""
        super().__init__()
        logger.debug("OllamaEmbedder initialized")

    async def create(
        self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    ) -> list[float]:
        """Create embeddings for input data via our Ollama client.

        Args:
            input_data: Text string, list of strings, or token IDs to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding call fails (propagates from our client)

        Note:
            graphiti_core typically calls this with single strings for node/edge
            embeddings. If a list is provided, we embed the first item.
        """
        # Handle different input types
        if isinstance(input_data, str):
            text_to_embed = input_data
        elif isinstance(input_data, list) and len(input_data) > 0:
            # If list of strings, embed the first one
            # graphiti_core typically passes single strings
            text_to_embed = str(input_data[0])
        else:
            # Handle edge cases (empty list, iterables, etc.)
            logger.warning(
                "Unexpected input_data type, converting to string",
                input_type=type(input_data),
            )
            text_to_embed = str(input_data)

        logger.debug(
            "Creating embedding",
            text_length=len(text_to_embed),
        )

        try:
            # Call our sync embed in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama_embed(input=text_to_embed),
            )

            # Extract embedding from response
            # Our embed() returns: {"embeddings": [[float, float, ...]]}
            embeddings = response.get("embeddings", [])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("No embeddings returned from Ollama")

            # Return first embedding vector
            embedding_vector = embeddings[0]
            logger.debug("Embedding created", vector_length=len(embedding_vector))

            return embedding_vector

        except Exception as e:
            logger.error(
                "Failed to create embedding",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
