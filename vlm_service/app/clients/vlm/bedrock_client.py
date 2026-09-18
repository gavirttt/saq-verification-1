"""AWS Bedrock adapter for the installation-assessment VLM call.

Implements `domain.interfaces.VLMClient` using Bedrock's Converse API, which
provides a single request/response shape across model families (Anthropic,
Amazon Nova, etc.) so this adapter isn't tied to one provider's native
payload format. As with `clients.vlm.client`, this module is the ONLY place
in the codebase that knows about boto3, the Bedrock request/response shape,
or the chosen model id — everything else only ever sees domain types.

`boto3` is synchronous, so calls are dispatched via `asyncio.to_thread` to
keep this adapter's public interface async and consistent with the OpenAI-compatible
client.
"""
from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.clients.vlm.normalize import normalize_assessment
from app.clients.vlm.prompt import SYSTEM_PROMPT, USER_PROMPT
from app.clients.vlm.schemas import try_parse_raw_payload
from app.core.logging import get_logger
from app.domain.errors import VLMResponseError, VLMUnavailableError
from app.domain.models import InstallationAssessment

logger = get_logger(__name__)

_MIME_TO_BEDROCK_FORMAT = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


class BedrockVLMClient:
    """Adapter talking to Amazon Bedrock's Converse API."""

    def __init__(
        self,
        model_id: str,
        region_name: str,
        max_tokens: int = 800,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.5,
        bedrock_client: "boto3.client" = None,  # type: ignore[valid-type]
    ) -> None:
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff_seconds
        # Allow injection of a pre-built client for tests; otherwise build
        # one from the standard AWS credential chain (env vars, shared
        # config/credentials files, or an instance/task IAM role).
        self._client = bedrock_client or boto3.client(
            "bedrock-runtime", region_name=region_name
        )

    def _build_converse_kwargs(self, image_bytes: bytes, mime_type: str) -> dict:
        image_format = _MIME_TO_BEDROCK_FORMAT.get(mime_type)
        if image_format is None:
            raise VLMResponseError(f"Unsupported image mime type for Bedrock: {mime_type}")

        return {
            "modelId": self._model_id,
            "system": [{"text": SYSTEM_PROMPT}],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"text": USER_PROMPT},
                        {"image": {"format": image_format, "source": {"bytes": image_bytes}}},
                    ],
                }
            ],
            "inferenceConfig": {"temperature": 0.0, "maxTokens": self._max_tokens},
        }

    async def assess_image(self, image_bytes: bytes, mime_type: str) -> InstallationAssessment:
        kwargs = self._build_converse_kwargs(image_bytes, mime_type)
        raw_text = await self._call_with_retries(kwargs)
        parsed = try_parse_raw_payload(raw_text)
        if parsed is None:
            raise VLMResponseError(
                f"Bedrock response could not be parsed as JSON: {raw_text[:200]!r}"
            )
        return normalize_assessment(parsed)

    def _invoke_sync(self, kwargs: dict) -> str:
        response = self._client.converse(**kwargs)
        content_blocks = response["output"]["message"]["content"]
        text = "".join(block.get("text", "") for block in content_blocks)
        return text

    async def _call_with_retries(self, kwargs: dict) -> str:
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                text = await asyncio.to_thread(self._invoke_sync, kwargs)
                if not text or not text.strip():
                    last_error = RuntimeError("Bedrock returned empty content")
                    logger.warning(
                        "Bedrock returned empty content (attempt %d/%d)",
                        attempt,
                        self._max_retries,
                    )
                else:
                    return text
            except ClientError as exc:
                last_error = exc
                error_code = exc.response.get("Error", {}).get("Code", "")
                status_code = exc.response.get("ResponseMetadata", {}).get(
                    "HTTPStatusCode", 0
                )
                logger.error(
                    "Bedrock rejected request (attempt %d/%d): %s - %s",
                    attempt,
                    self._max_retries,
                    error_code,
                    exc,
                )
                # Throttling and transient 5xx-equivalents are retryable;
                # anything else (bad request, access denied, validation
                # errors, model-not-found) fails fast since retrying won't
                # help.
                retryable_codes = {
                    "ThrottlingException",
                    "ServiceUnavailableException",
                    "ModelTimeoutException",
                    "InternalServerException",
                }
                if error_code not in retryable_codes and status_code < 500:
                    raise VLMUnavailableError(
                        f"Bedrock rejected request: {error_code or status_code} - {exc}"
                    ) from exc
            except BotoCoreError as exc:
                last_error = exc
                logger.warning(
                    "Bedrock call failed (attempt %d/%d): %s",
                    attempt,
                    self._max_retries,
                    exc,
                )
            except (KeyError, IndexError) as exc:
                raise VLMResponseError(f"Malformed Bedrock response envelope: {exc}") from exc

            if attempt < self._max_retries:
                await asyncio.sleep(self._retry_backoff * (2 ** (attempt - 1)))

        raise VLMUnavailableError(
            f"Bedrock unreachable/unresponsive after {self._max_retries} attempts: {last_error}"
        )
