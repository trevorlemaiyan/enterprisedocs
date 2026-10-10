"""Provider interface and factory.

Business logic talks to `LLMProvider.chat()` only, so switching model or vendor is a
configuration change (LLM_PROVIDER / LLM_MODEL), not a code change.
"""

from abc import ABC, abstractmethod

from app.config import Settings, get_settings


class LLMError(Exception):
    """The model service failed or returned something unusable."""


class LLMConfigError(LLMError):
    """The LLM is not configured (missing model name or API key)."""


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Send a conversation and return the assistant message dict.

        The returned dict follows the OpenAI chat format: it has `content` and, when the
        model wants to call tools, a `tool_calls` list.
        """


def get_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    name = settings.llm_provider.strip().lower()

    if not settings.llm_model:
        raise LLMConfigError("LLM_MODEL is not set.")

    common = {"model": settings.llm_model, "timeout": settings.llm_timeout_seconds}

    if name == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMConfigError("OPENROUTER_API_KEY is not set.")
        from app.llm.openrouter import OpenRouterProvider

        return OpenRouterProvider(api_key=settings.openrouter_api_key, **common)

    if name == "openai":
        if not settings.openai_api_key:
            raise LLMConfigError("OPENAI_API_KEY is not set.")
        from app.llm.openai import OpenAIProvider

        return OpenAIProvider(api_key=settings.openai_api_key, **common)

    raise LLMConfigError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'.")
