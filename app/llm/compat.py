"""Client for any OpenAI-compatible /chat/completions API (OpenRouter, OpenAI, ...)."""

import logging

import httpx

from app.llm.provider import LLMError, LLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    DEFAULT_BASE_URL = ""
    EXTRA_HEADERS: dict[str, str] = {}

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 60.0,
        temperature: float = 0.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.temperature = temperature
        self._client = client or httpx.Client(timeout=timeout)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Authorization": f"Bearer {self.api_key}", **self.EXTRA_HEADERS}

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Request to LLM failed: {type(exc).__name__}") from exc

        if response.status_code >= 400:
            # Log the provider's explanation, but keep it out of the exception that reaches clients.
            logger.error("LLM API error %s: %s", response.status_code, response.text[:500])
            raise LLMError(f"LLM API returned HTTP {response.status_code}")

        try:
            body = response.json()
            if "error" in body:
                logger.error("LLM API error body: %s", str(body["error"])[:500])
                raise LLMError("LLM API returned an error")
            return body["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM API returned a malformed response") from exc
