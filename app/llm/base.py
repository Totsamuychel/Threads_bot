"""Base LLM client abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    text: str
    model: str
    tokens_used: Optional[int] = None
    generation_time: Optional[float] = None
    raw_response: Optional[dict] = None
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if generation was successful."""
        return self.error is None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = "default", 
                 temperature: float = 0.7, max_tokens: int = 500, timeout: int = 60):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
    
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                      temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> LLMResponse:
        """
        Generate text from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            LLMResponse with generated text and metadata
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if LLM service is available."""
        pass
    
    def _get_temperature(self, override: Optional[float]) -> float:
        """Get temperature value, using override if provided."""
        return override if override is not None else self.temperature
    
    def _get_max_tokens(self, override: Optional[int]) -> int:
        """Get max tokens value, using override if provided."""
        return override if override is not None else self.max_tokens
