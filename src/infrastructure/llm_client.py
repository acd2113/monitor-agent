from openai import OpenAI

from src.config import settings
from src.utils import extract_json


class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.llm_api_key or "EMPTY",
            base_url=settings.llm_base_url or None,
            timeout=settings.llm_timeout,
            max_retries=settings.max_retries,
        )
        self.model = settings.llm_model

    def chat(self, messages, temperature=0.1, json_mode=False):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_json(self, messages, temperature=0.1):
        raw = self.chat(messages, temperature=temperature, json_mode=True)
        return extract_json(raw)
