from app.llm.compat import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = "https://api.openai.com/v1"
