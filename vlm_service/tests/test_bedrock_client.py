"""Tests for BedrockVLMClient's request-building and response-parsing logic,
using a fake object that mimics the boto3 bedrock-runtime client's
`.converse()` method. No real AWS credentials or network calls involved."""
from __future__ import annotations

import json

import pytest
from botocore.exceptions import ClientError

from app.clients.vlm.bedrock_client import BedrockVLMClient
from app.domain.enums import InstallationStatus
from app.domain.errors import VLMResponseError, VLMUnavailableError


def _converse_response(payload: dict) -> dict:
    return {
        "output": {
            "message": {
                "content": [{"text": json.dumps(payload)}],
            }
        }
    }


class FakeBedrockRuntimeClient:
    """Mimics boto3's bedrock-runtime client `.converse()` call."""

    def __init__(self, responses: list) -> None:
        # Each item is either a dict response or an Exception instance to raise.
        self._responses = list(responses)
        self.calls: list[dict] = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.mark.asyncio
async def test_bedrock_client_parses_installation_assessment():
    payload = {
        "installation_status": "pass",
        "device_power_status": "green",
        "workmanship_quality": "acceptable",
        "compliance_flags": [],
        "technical_observations": [],
        "confidence": 0.95,
        "raw_description": "valid installation",
    }
    fake_client = FakeBedrockRuntimeClient([_converse_response(payload)])
    client = BedrockVLMClient(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1",
        bedrock_client=fake_client,
    )

    result = await client.assess_image(b"fake-jpeg-bytes", "image/jpeg")

    assert result.installation_status == InstallationStatus.PASS
    assert result.confidence == 0.95
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["modelId"] == "amazon.nova-lite-v1:0"


@pytest.mark.asyncio
async def test_bedrock_client_retries_on_throttling_then_succeeds():
    payload = {
        "installation_status": "fail",
        "device_power_status": "red",
        "mess_types": ["unsecured_cables"],
        "technical_observations": ["cables are not ziptied"],
        "confidence": 0.8,
        "raw_description": "Cluttered.",
    }
    throttle_error = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}, "ResponseMetadata": {}},
        "Converse",
    )
    fake_client = FakeBedrockRuntimeClient([throttle_error, _converse_response(payload)])
    client = BedrockVLMClient(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1",
        retry_backoff_seconds=0.01,
        bedrock_client=fake_client,
    )

    result = await client.assess_image(b"fake-jpeg-bytes", "image/jpeg")

    assert result.installation_status == InstallationStatus.FAIL
    assert len(fake_client.calls) == 2


@pytest.mark.asyncio
async def test_bedrock_client_fails_fast_on_validation_error():
    validation_error = ClientError(
        {
            "Error": {"Code": "ValidationException", "Message": "bad request"},
            "ResponseMetadata": {"HTTPStatusCode": 400},
        },
        "Converse",
    )
    fake_client = FakeBedrockRuntimeClient([validation_error])
    client = BedrockVLMClient(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1",
        max_retries=3,
        bedrock_client=fake_client,
    )

    with pytest.raises(VLMUnavailableError):
        await client.assess_image(b"fake-jpeg-bytes", "image/jpeg")

    # Fails fast: does not exhaust all retries for a non-retryable error.
    assert len(fake_client.calls) == 1


@pytest.mark.asyncio
async def test_bedrock_client_raises_response_error_on_unparsable_json():
    fake_client = FakeBedrockRuntimeClient(
        [_converse_response_raw_text("not json at all")]
    )
    client = BedrockVLMClient(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1",
        bedrock_client=fake_client,
    )

    with pytest.raises(VLMResponseError):
        await client.assess_image(b"fake-jpeg-bytes", "image/jpeg")


def _converse_response_raw_text(text: str) -> dict:
    return {"output": {"message": {"content": [{"text": text}]}}}
