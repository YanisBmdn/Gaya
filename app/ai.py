import os
import json

from abc import ABC, abstractmethod
from enum import Enum

from openai import OpenAI
from anthropic import Anthropic
from pydantic import BaseModel
from typing import Type, Dict

from .constants import GPT_4o_MINI, SONNET_3_5, DEVELOPER, USER
from .prompts import OUTPUT_LANGUAGE_PROMPT, ANTHROPIC_SYSTEM_PROMPT, ANTHROPIC_STRUCTURED_OUTPUT_PROMPT
from .utils import handle_exceptions
import tiktoken

enc = tiktoken.encoding_for_model(GPT_4o_MINI)

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class LLMClient(ABC):
    """
    Abstract class for a Language Model client
    """

    def __init__(self, client):
        self.client = client
        self.input_token = 0
        self.output_token = 0
    
    def get_total_tokens(self):
        return self.input_token, self.output_token

    def reset_token_count(self):
        self.input_tokens = 0
        self.output_tokens = 0

    @abstractmethod
    def completion(self, messages: list[Dict[str, str]], max_tokens: int = 100) -> str:
        """
        Generate a completion from the language model
        
        Args:
            messages (list[Dict[str, str]]): List of messages to generate completion from
            max_tokens (int): Maximum tokens to generate in the completion
        
        Returns
            str: Completion generated from the language model
        """
        pass

    @abstractmethod
    def structured_completion(self, messages: list[Dict[str, str]], response_format: Type[BaseModel], max_tokens: int = 100) -> BaseModel:
        """
        Generate a structured completion from the language model

        Args:
            messages (list[Dict[str, str]]): List of messages to generate completion from
            response_format (Type[BaseModel]): Pydantic model to validate the response
            max_tokens (int): Maximum tokens to generate in the completion
        Returns:
            BaseModel: Pydantic model of the completion generated from the language model
        """
        pass


class OpenAIClient(LLMClient):
    """
    OpenAI Language Model client
    """

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
        messages.insert(1, {"role": DEVELOPER, "content": ANTHROPIC_SYSTEM_PROMPT})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.input_token += response.usage.prompt_tokens
        self.output_token += response.usage.completion_tokens
        return response.choices[0].message.content

    @handle_exceptions(default_return=None)
    def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_format: Type[BaseModel],
        model: str = GPT_4o_MINI,
        max_tokens: int = 100,
        max_completion_tokens: int = None,
        temperature: int = 1,
    ) -> BaseModel:
        """ """
        messages.insert(0, {"role": DEVELOPER, "content": OUTPUT_LANGUAGE_PROMPT})
        messages.insert(1, {"role": DEVELOPER, "content": ANTHROPIC_SYSTEM_PROMPT})

        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            response_format=response_format,
        )

        self.input_token += response.usage.prompt_tokens
        self.output_token += response.usage.completion_tokens
        return response.choices[0].message.parsed


class AnthropicClient(LLMClient):
    """
    Anthropic Language Model client
    """

    def __init__(self):
        super().__init__(Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY")))
    
    def _convert_to_anthropic_format(self, messages: list[Dict[str, str]]) -> list[Dict[str, str]]:
        """
        Convert messages from OpenAI format to Anthropic format

        Args: 
            messages (list[Dict[str, str]]): List of messages in OpenAI format
        Returns:
            tuple[str, list[Dict[str, str]]]: Tuple of system prompt and messages in Anthropic format
        """

        for i, message in enumerate(messages):
            if message["role"] == DEVELOPER:
                messages[i]["role"] = USER

        return messages


    @handle_exceptions(default_return="")
    def completion(self, messages: list[Dict[str, str]], max_tokens: int = 100, temperature=.9) -> str:
        self._convert_to_anthropic_format(messages)

        messages.insert(0, {"role": USER, "content": OUTPUT_LANGUAGE_PROMPT})
        response = self.client.messages.create(
            model=SONNET_3_5,
            system=ANTHROPIC_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        self.input_token += response.usage.input_tokens
        self.output_token += response.usage.output_tokens

        return response.content[0].text
    
    @handle_exceptions(default_return=None)
    def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_format: Type[BaseModel],
        model: str = SONNET_3_5,
        max_tokens: int = 1024,
        temperature: float = .9,
    ) -> BaseModel:
        messages = self._convert_to_anthropic_format(messages)

        output_format_prompt = ANTHROPIC_STRUCTURED_OUTPUT_PROMPT.format(response_format=f"{response_format.__name__}\n{response_format.model_json_schema()}")
        messages.append({
            "role": USER,
            "content": output_format_prompt
        })

        response = self.client.messages.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            system=ANTHROPIC_SYSTEM_PROMPT,
            temperature=temperature
        )

        self.input_token += response.usage.input_tokens
        self.output_token += response.usage.output_tokens

        # Parse the response into JSON and then into the Pydantic model
        try:
            json_response = json.loads(response.content[0].text)
            return response_format.model_validate(json_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse response into {response_format.__name__}: {str(e)}")


openai_client = OpenAIClient()
anthropic_client = AnthropicClient()
