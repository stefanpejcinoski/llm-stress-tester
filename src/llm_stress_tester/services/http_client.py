"""Non-streaming HTTP client for OpenAI-compatible API."""

from __future__ import annotations

from httpx import AsyncClient, Response


async def send_request(
    client: AsyncClient,
    url: str,
    model: str,
    messages: list[dict],
    timeout: float,
) -> tuple[Response, float]:
    """Send a non-streaming chat completion request.

    Returns (response, latency_ms).
    """
    import time as _time
    start = _time.monotonic()
    resp = await client.post(
        url,
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": 0.0,
        },
        timeout=timeout,
    )
    latency_ms = (_time.monotonic() - start) * 1000
    return resp, latency_ms
