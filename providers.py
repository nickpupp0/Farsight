"""
LLM provider abstraction for llm-fuzzer.

Each provider exposes a single method, generate(system_prompt, user_prompt),
so the rest of the tool doesn't need to know or care which backend is
actually running. No sampling parameters (temperature/top_p/top_k) are
sent anywhere -- variety in this tool comes entirely from the technique
catalog in techniques.py, not from sampling knobs. That also sidesteps
current-generation Claude models (Sonnet 5+) rejecting those parameters
outright.

Add a new backend by subclassing LLMProvider and registering it in
PROVIDERS below.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional


class ProviderError(RuntimeError):
    """Raised when a provider can't be initialized or a call fails."""


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a single completion string."""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini"):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ProviderError(
                "The 'openai' package is required for --provider openai. "
                "Install it with: pip install openai"
            ) from e

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError(
                "OPENAI_API_KEY is missing. Set it in a .env file or environment variable."
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            raise ProviderError(f"OpenAI request failed: {e}") from e
        return response.choices[0].message.content.strip()


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, model: str = "claude-sonnet-5"):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ProviderError(
                "The 'anthropic' package is required for --provider claude. "
                "Install it with: pip install anthropic"
            ) from e

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is missing. Set it in a .env file or environment variable."
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                # This is short-form text generation, not a reasoning task --
                # adaptive thinking is on by default on current Claude models and
                # would just add latency/cost with no benefit here.
                thinking={"type": "disabled"},
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as e:
            raise ProviderError(f"Claude request failed: {e}") from e
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model: str = "llama3.1"):
        try:
            import ollama
        except ImportError as e:
            raise ProviderError(
                "The 'ollama' package is required for --provider ollama. "
                "Install it with: pip install ollama\n"
                "Also make sure the Ollama daemon/app is running locally."
            ) from e

        self._ollama = ollama
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            client = self._ollama.Client(host=self.host)
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            raise ProviderError(
                f"Ollama request failed: {e}\n"
                f"Is the Ollama daemon running at {self.host}, and have you pulled "
                f"the model with `ollama pull {self.model}`?"
            ) from e
        return response["message"]["content"].strip()


PROVIDERS = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "ollama": OllamaProvider,
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "claude": "claude-sonnet-5",
    "ollama": "llama3.1",
}


def get_provider(name: str, model: Optional[str] = None) -> LLMProvider:
    if name not in PROVIDERS:
        raise ProviderError(f"Unknown provider '{name}'. Choose from: {', '.join(PROVIDERS)}")
    model = model or DEFAULT_MODELS[name]
    return PROVIDERS[name](model=model)
