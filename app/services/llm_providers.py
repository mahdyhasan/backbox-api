"""
LLM Provider Interface and Implementations
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator
import anthropic
import groq


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
    async def generate(
        self,
        model: str,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False
    ) -> AsyncIterator[str] | str:
        """Generate completion, optionally streaming"""
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str, model: str) -> int:
        """Estimate token count for text"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com"):
        super().__init__(api_key, base_url)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
    
    async def generate(
        self,
        model: str,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False
    ) -> AsyncIterator[str] | str:
        """Generate with Claude"""
        # Convert messages to Claude format
        system_msg = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        if stream:
            async def stream_generator():
                async with self.client.messages.stream(
                    model=model,
                    messages=user_messages,
                    system=system_msg,
                    max_tokens=max_tokens,
                    temperature=temperature
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
            return stream_generator()
        else:
            response = await self.client.messages.create(
                model=model,
                messages=user_messages,
                system=system_msg,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.content[0].text
    
    async def count_tokens(self, text: str, model: str) -> int:
        """Estimate tokens (rough approximation for Claude)"""
        # Claude uses ~4 chars per token approximation
        # In production, use Anthropic's tokenizer
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """Check Anthropic health"""
        try:
            await self.client.messages.create(
                model="claude-haiku-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}]
            )
            return True
        except Exception:
            return False


class GroqProvider(LLMProvider):
    """Groq provider implementation"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.groq.com"):
        super().__init__(api_key, base_url)
        self.client = groq.AsyncGroq(api_key=api_key)
    
    async def generate(
        self,
        model: str,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False
    ) -> AsyncIterator[str] | str:
        """Generate with Groq"""
        if stream:
            async def stream_generator():
                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            return stream_generator()
        else:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            return response.choices[0].message.content
    
    async def count_tokens(self, text: str, model: str) -> int:
        """Estimate tokens (rough approximation for Llama)"""
        # Llama uses ~4 chars per token approximation
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """Check Groq health"""
        try:
            await self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=10
            )
            return True
        except Exception:
            return False


def get_provider(provider_name: str, api_key: str, base_url: str) -> LLMProvider:
    """Factory function to get provider instance"""
    providers = {
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
        # Add more providers here
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return provider_class(api_key, base_url)