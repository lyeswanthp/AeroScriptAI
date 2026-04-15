"""VLM service with LM Studio adapter, retry logic, and streaming support."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import httpx

from app.config import settings
from app.exceptions import LMStudioUnavailableError, ModelBusyError

logger = logging.getLogger(__name__)


class VLMProvider(ABC):
    """Abstract interface for VLM providers."""

    @abstractmethod
    async def recognize(
        self,
        image_b64: str,
        messages: list[dict],
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Send an image and messages to the VLM, yield tokens."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...


class LMStudioAdapter(VLMProvider):
    """
    Adapter for LM Studio's OpenAI-compatible API.

    Handles:
    - OpenAI-compatible /v1/chat/completions endpoint
    - Streaming via SSE
    - Retry with exponential backoff on transient errors
    - Request semaphore to prevent concurrent calls
    - Request timeout
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(1)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.lm_studio_base_url,
                timeout=httpx.Timeout(settings.request_timeout_seconds),
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Ping LM Studio's /v1/models endpoint."""
        try:
            client = await self._get_client()
            response = await client.get("/v1/models")
            return response.status_code == 200
        except (httpx.HTTPError, asyncio.TimeoutError):
            return False

    async def recognize(
        self,
        image_b64: str,
        messages: list[dict],
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Send a request to LM Studio and yield tokens.

        Builds the multi-part content array with text + image,
        following the OpenAI vision-compatible format.
        """
        # Build content array: text + image
        content = []
        for msg in messages:
            if isinstance(msg.get("content"), str):
                content.append({"type": "text", "text": msg["content"]})

        # Add image as the last user message
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
        })

        # Assemble request payload
        payload = {
            "model": settings.model_name,
            "messages": [{"role": "system", "content": messages[0]["content"] if messages else ""}]
                     + [{"role": "user", "content": content}],
            "stream": stream,
            "max_tokens": settings.max_tokens,
        }

        # Try to acquire semaphore
        async with self._semaphore:
            client = await self._get_client()
            async for token in self._stream_response(client, payload):
                yield token

    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        payload: dict,
    ) -> AsyncGenerator[str, None]:
        """
        Internal: send request and yield tokens from the stream.
        Handles retry and timeout.
        """
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                async with client.stream(
                    "POST",
                    "/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=settings.request_timeout_seconds,
                ) as response:
                    if response.status_code == 503:
                        raise LMStudioUnavailableError(
                            message="Model is not loaded in LM Studio",
                            detail="Load a vision-capable model in LM Studio and ensure the server is running.",
                        )

                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line == "data: [DONE]":
                            break

                        if line.startswith("data: "):
                            line = line[6:]  # strip "data: "

                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield content

                    return  # Success

            except (httpx.HTTPStatusError, httpx.RequestError, asyncio.TimeoutError) as e:
                last_error = e
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"LM Studio request failed (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
                continue

        # All retries exhausted
        if last_error:
            raise LMStudioUnavailableError(
                message="LM Studio request failed after retries",
                detail=str(last_error),
            )


# Singleton instance
vlm_service = LMStudioAdapter()
