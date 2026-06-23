import os
from abc import ABC, abstractmethod
from google import genai
from openai import OpenAI
from anthropic import Anthropic 
from groq import Groq

class BaseLLM(ABC):
    """ BaseLLM class to ensure every providers shares the same signature """
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        pass


class OpenAIProvider(BaseLLM):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content


class GeminiProvider(BaseLLM):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{system_prompt}\n\nUser Request: {user_prompt}"
        )
        return response.text


class GroqProvider(BaseLLM):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
        )
        return completion.choices[0].message.content 


class AnthropicProvider(BaseLLM):
    def __init__(self, api_key: str, model: str):
        self.client = Anthropic(api_key=api_key)
        self.model = model or "claude-3-5-sonnet-latest"

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt, # Anthropic passes system prompts as a top-level param
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        return response.content[0].text 


class LLMFactory:
    """ Dynamically fetch engine wrapper """
    _PROVIDERS = {
            "groq": GroqProvider,
            "gemini": GeminiProvider,
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "claude": AnthropicProvider,
            "google": GeminiProvider
        }

    @staticmethod
    def get_provider(provider_name: str, api_key: str, model_name: str = None) -> BaseLLM:
        norm_name = provider_name.lower().strip()
        provider_class = LLMFactory._PROVIDERS.get(norm_name)

        if not provider_class:
            support_engines = ", ".join(f"'{k}'" for k in LLMFactory._PROVIDERS.keys())
            raise ValueError(
                f"Unsupported LLM provider selection: '{provider_name}'. "
                f"Supported choices are: {supported_engines}"
            )

        return provider_class(api_key=api_key, model=model_name)



