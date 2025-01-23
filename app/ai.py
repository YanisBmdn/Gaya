import os

from abc import ABC, abstractmethod
from enum import Enum

from openai import OpenAI
from anthropic import Anthropic
from pydantic import BaseModel
from typing import Type, Dict

from .constants import DEVELOPER, GPT_4o_MINI, SONNET_3_5
from .prompts import OUTPUT_LANGUAGE_PROMPT
from .utils import handle_exceptions


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient(ABC):
    """ """

    def __init__(self, client):
        self.client = client

    @abstractmethod
    def completion(self, messages: list[Dict[str, str]], max_tokens: int = 100) -> str:
        pass


class OpenAIClient(LLMClient):
    """ """

    def __init__(self):
        super().__init__(OpenAI(api_key=os.environ.get("OPENAI_API_KEY")))

    @handle_exceptions(default_return="")
    def completion(
        self,
        messages: list[Dict[str, str]],
        model: str = GPT_4o_MINI,
        max_tokens: int = 100,
        temperature: int = 1,
    ) -> str:
        messages.insert(0, {"role": DEVELOPER, "content": OUTPUT_LANGUAGE_PROMPT})
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    @handle_exceptions(default_return=None)
    def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_format: Type[BaseModel],
        model: str = GPT_4o_MINI,
        max_tokens: int = 100,
        temperature: int = 1,
    ) -> BaseModel:
        """ """
        messages.insert(0, {"role": DEVELOPER, "content": OUTPUT_LANGUAGE_PROMPT})
        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )

        return response.choices[0].message.parsed


class AnthropicClient(LLMClient):
    """ """

    def __init__(self):
        super().__init__(Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY")))

    @handle_exceptions(default_return="")
    def completion(self, messages: list[Dict[str, str]], max_tokens: int = 100) -> str:
        response = self.client.messages.create(
            model=SONNET_3_5,
            messages=messages,
            max_tokens=max_tokens,
        )

        return response.content
