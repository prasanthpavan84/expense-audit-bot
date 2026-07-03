from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMProvider(ABC):
    """Abstract base class for language model providers.

    Concrete implementations must provide a ``generate`` method that accepts a prompt
    and optional parameters and returns a dictionary containing at least ``output``
    (the generated text) and optionally ``usage`` information.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate a completion for the given ``prompt``.

        Args:
            prompt: The input text to the model.
            **kwargs: Provider‑specific parameters (e.g., temperature, max_tokens).

        Returns:
            A dictionary with keys like ``output`` and ``usage``.
        """
        raise NotImplementedError


class MockProvider(LLMProvider):
    """A simple deterministic mock provider for testing.

    Returns the prompt prefixed with ``[Mock]`` and includes a dummy usage
    payload. This enables unit tests without external API calls.
    """

    def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        output = f"[Mock] {prompt}"
        usage = {"prompt_tokens": len(prompt.split()), "completion_tokens": len(output.split())}
        return {"output": output, "usage": usage}


class GeminiProvider(LLMProvider):
    """LLM provider wrapper for Google's Gemini API."""

    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: str | None = None):
        import os
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        # For evaluation/testing, we can import and call google.genai or return mocked responses
        # if GEMINI_API_KEY is not set.
        if not self.api_key:
            # Fall back to mock behaviour to avoid raising API errors in test environments
            output = f"[Mock Gemini: {self.model_name}] {prompt}"
            return {
                "output": output,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0}
            }
        
        # Real call using google.genai or google.adk (if needed)
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                **kwargs
            )
            return {
                "output": response.text,
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0
                }
            }
        except Exception as e:
            from core.exceptions import LLMProviderError
            raise LLMProviderError(f"Gemini generation failed: {e}")

