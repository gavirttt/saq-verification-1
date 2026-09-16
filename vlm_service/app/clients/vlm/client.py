"""HTTP adapter for the locally-hosted, OpenAI-compatible VLM.

This is the ONLY module in the codebase that knows the VLM's base URL,
payload shape, or response format. It implements `domain.interfaces.VLMClient`
and returns/raises only domain types.
"""
from __future__ import annotations

import asyncio
import base64

import httpx

from app.clients.vlm.normalize import normalize_assessment
from app.clients.vlm.prompt import SYSTEM_PROMPT, USER_PROMPT
from app.clients.vlm.schemas import (
    ChatCompletionRequest,
    ChatMessage,
    ChatMessageContent,
    try_parse_raw_payload,
)
from app.core.logging import get_logger
from app.domain.errors import VLMResponseError, VLMUnavailableError
from app.domain.models import CleanlinessAssessment

logger = get_logger(__name__)


class OpenAICompatibleVLMClient:
    """Adapter talking to an OpenAI-compatible `/chat/completions` endpoint."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.5,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff_seconds
        # Allow injection of a shared/test client; otherwise own one lazily.
        self._external_client = http_client

    def _build_request(self, image_bytes: bytes, mime_type: str) -> ChatCompletionRequest:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{b64}"
        return ChatCompletionRequest(
            model=self._model,
            messages=[
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(
                    role="user",
                    content=[
                        ChatMessageContent(type="text", text=USER_PROMPT),
                        ChatMessageContent(type="image_url", image_url={"url": data_url}),
                    ],
                ),
            ],
            temperature=0.0,
            max_tokens=800,
            response_format={"type": "text"},
        )

    async def assess_image(self, image_bytes: bytes, mime_type: str) -> CleanlinessAssessment:
        payload = self._build_request(image_bytes, mime_type)
        raw_text = await self._call_with_retries(payload)
        parsed = try_parse_raw_payload(raw_text)
        if parsed is None:
            raise VLMResponseError(
                f"VLM response could not be parsed as JSON: {raw_text[:200]!r}"
            )
        return normalize_assessment(parsed)

    async def _call_with_retries(self, payload: ChatCompletionRequest) -> str:
        last_error: Exception | None = None
        client = self._external_client
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        try:
            for attempt in range(1, self._max_retries + 1):
                try:
                    response = await client.post(
                        "/chat/completions",
                        json=payload.model_dump(exclude_none=True),
                    )
                    response.raise_for_status()
                    body = response.json()
                    content = body["choices"][0]["message"]["content"]
                    if not content or not content.strip():
                        last_error = RuntimeError("VLM returned empty content")
                        logger.warning(
                            "VLM returned empty content (attempt %d/%d), finish_reason=%s",
                            attempt,
                            self._max_retries,
                            body["choices"][0].get("finish_reason"),
                        )
                        if attempt < self._max_retries:
                            await asyncio.sleep(self._retry_backoff * (2 ** (attempt - 1)))
                            continue
                        raise VLMResponseError(
                            "VLM returned empty content after "
                            f"{self._max_retries} attempts"
                        )
                    return content
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    logger.warning(
                        "VLM call failed (attempt %d/%d): %s",
                        attempt,
                        self._max_retries,
                        exc,
                    )
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    body_text = exc.response.text[:1000]
                    logger.error(
                        "VLM rejected request: HTTP %s body=%s",
                        exc.response.status_code,
                        body_text,
                    )
                    if exc.response.status_code < 500:
                        raise VLMUnavailableError(
                            f"VLM rejected request: HTTP {exc.response.status_code} - {body_text}"
                        ) from exc
                    logger.warning(
                        "VLM call failed (attempt %d/%d): HTTP %s",
                        attempt,
                        self._max_retries,
                        exc.response.status_code,
                    )
                except (KeyError, IndexError, ValueError) as exc:
                    raise VLMResponseError(f"Malformed VLM response envelope: {exc}") from exc

                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_backoff * (2 ** (attempt - 1)))

            raise VLMUnavailableError(
                f"VLM unreachable after {self._max_retries} attempts: {last_error}"
            )
        finally:
            if owns_client:
                await client.aclose()
