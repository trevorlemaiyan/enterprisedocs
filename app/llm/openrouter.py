from app.llm.compat import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter exposes many models (including Qwen) behind one OpenAI-compatible API."""

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    EXTRA_HEADERS = {"X-Title": "EnterpriseDocs AI"}
